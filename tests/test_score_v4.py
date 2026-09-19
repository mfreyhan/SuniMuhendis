"""
Tests for Score V4 and the widened heat-exchanger design space.

V4 exists to fix a structural problem the physics audit found: under V1-V3,
85% of the weight sat on requirements that pay in full the moment they are met,
so the score for merely reaching a feasible design never moved off 0.439
whatever the targets were. These tests pin the properties that fix is supposed
to have.
"""

import json
import os

import pytest

from sunimuhendis import make_env
from sunimuhendis.environments.heat_exchanger.drc import run_heat_exchanger_drc
from sunimuhendis.environments.heat_exchanger.score import get_score_function
from sunimuhendis.environments.heat_exchanger.simulator import HeatExchangerSimulator


TASK = {
    "task_id": "score_v4_test",
    "score_version": "heat_exchanger_score_v4",
    "target_heat_duty": 250000.0,
    "max_dp_tube": 10000.0,
    "max_dp_shell": 10000.0,
    "gate_share": 0.30,
    "cost_good": 2000.0,
    "cost_bad": 20000.0,
    "warning_penalty_per_warning": 0.10,
}

# The design the deliberate search found: meets every requirement with no
# warnings and a cost well inside the good band.
CLEAN_DESIGN = {
    "geometry_type": "shell_and_tube",
    "length": 3.8296,
    "inner_tube_di": 0.01008,
    "inner_tube_do": 0.0127,
    "outer_shell_di": 0.29609,
    "number_of_tubes": 94,
    "baffle_spacing": 0.92906,
    "tube_passes": 2,
    "pitch_ratio": 1.28277,
    "baffle_cut": 0.22988,
    "pitch_type": "triangular",
    "D_nozzle_hot": 0.04245,
    "D_nozzle_cold": 0.04245,
}


@pytest.fixture(scope="module")
def env():
    return make_env("heat_exchanger", score_version="heat_exchanger_score_v4")


@pytest.fixture(scope="module")
def score():
    return get_score_function("heat_exchanger_score_v4")


def metrics(**overrides):
    base = {
        "heat_duty_W": 260000.0,
        "dp_tube_Pa": 8000.0,
        "dp_shell_Pa": 3000.0,
        "effectiveness": 0.414,
        "cost_annualised_USD_per_yr": 2000.0,
        "num_warnings": 0.0,
    }
    base.update(overrides)
    return base


# ── The gate ─────────────────────────────────────────────────────────

def test_invalid_design_scores_zero(score):
    result = score.calculate_score(TASK, {}, is_valid=False, error_message="boom")
    assert result.normalized_total == 0.0
    assert not result.is_valid


def test_passing_the_gate_with_worthless_quality_pays_exactly_the_gate_share(score):
    """The floor for a feasible design is the gate share and nothing more."""
    result = score.calculate_score(
        TASK, metrics(cost_annualised_USD_per_yr=1e9, num_warnings=99.0))
    assert result.normalized_total == pytest.approx(0.30)
    assert result.components["gate_passed"] == 1.0


def test_missing_a_requirement_caps_the_score_at_the_gate_share(score):
    result = score.calculate_score(TASK, metrics(heat_duty_W=200000.0))
    assert result.normalized_total < 0.30
    assert result.components["num_unmet_requirements"] == 1.0
    assert "heat duty" in result.error_message


def test_the_gate_boundary_is_continuous_not_a_cliff(score):
    """A near miss and a bare pass land in the same place, so there is no jump."""
    near_miss = score.calculate_score(
        TASK, metrics(heat_duty_W=249999.0,
                      cost_annualised_USD_per_yr=1e9, num_warnings=99.0))
    bare_pass = score.calculate_score(
        TASK, metrics(heat_duty_W=250000.0,
                      cost_annualised_USD_per_yr=1e9, num_warnings=99.0))
    assert bare_pass.normalized_total - near_miss.normalized_total < 1e-5


def test_exceeding_the_duty_target_earns_nothing_extra(score):
    at_target = score.calculate_score(TASK, metrics(heat_duty_W=250000.0))
    way_over = score.calculate_score(TASK, metrics(heat_duty_W=360000.0))
    assert at_target.normalized_total == way_over.normalized_total


def test_every_requirement_must_be_met(score):
    for key, value in (("heat_duty_W", 100.0),
                       ("dp_tube_Pa", 50000.0),
                       ("dp_shell_Pa", 50000.0)):
        result = score.calculate_score(TASK, metrics(**{key: value}))
        assert result.components["gate_passed"] == 0.0, key


# ── Quality, past the gate ───────────────────────────────────────────

def test_a_perfect_design_scores_one(score):
    result = score.calculate_score(
        TASK, metrics(cost_annualised_USD_per_yr=500.0, num_warnings=0.0))
    assert result.normalized_total == pytest.approx(1.0)


def test_cost_moves_the_score_continuously(score):
    scores = [
        score.calculate_score(TASK, metrics(cost_annualised_USD_per_yr=c)).normalized_total
        for c in (2000.0, 6000.0, 11000.0, 16000.0, 20000.0)
    ]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == pytest.approx(1.0)
    assert scores[-1] == pytest.approx(0.30)


def test_each_warning_costs_a_tenth_of_the_quality_term(score):
    clean = score.calculate_score(TASK, metrics(num_warnings=0.0)).normalized_total
    one = score.calculate_score(TASK, metrics(num_warnings=1.0)).normalized_total
    assert clean - one == pytest.approx(0.70 * 0.10)


def test_effectiveness_does_not_affect_the_score(score):
    """
    Effectiveness is heat_duty / 627300 exactly, so scoring it would pay twice
    for the duty the gate already requires.
    """
    low = score.calculate_score(TASK, metrics(effectiveness=0.10))
    high = score.calculate_score(TASK, metrics(effectiveness=0.90))
    assert low.normalized_total == high.normalized_total


def test_effectiveness_is_duty_over_a_constant(env):
    """The reason effectiveness is not scored — verified against the simulator."""
    result = env.evaluate("t", TASK, "d", CLEAN_DESIGN)
    ratio = result.metrics["heat_duty_W"] / result.metrics["effectiveness"]
    assert ratio == pytest.approx(627300.0, rel=1e-9)


# ── Configuration is validated ───────────────────────────────────────

@pytest.mark.parametrize("bad", [
    {"gate_share": 1.5},
    {"target_heat_duty": 0.0},
    {"max_dp_tube": -1.0},
    {"cost_good": 5000.0, "cost_bad": 1000.0},
    {"warning_penalty_per_warning": -0.1},
])
def test_invalid_task_configuration_is_rejected(score, bad):
    with pytest.raises(ValueError):
        score.calculate_score(dict(TASK, **bad), metrics())


# ── The widened design space ─────────────────────────────────────────

def test_seven_field_design_still_validates(env):
    seven = {k: CLEAN_DESIGN[k] for k in (
        "geometry_type", "length", "inner_tube_di", "inner_tube_do",
        "outer_shell_di", "number_of_tubes", "baffle_spacing")}
    ok, message = env.validate_schema(seven)
    assert ok, message


def test_optional_fields_are_accepted(env):
    ok, message = env.validate_schema(CLEAN_DESIGN)
    assert ok, message


def test_explicit_null_means_use_the_default(env):
    """A model writing "tube_passes": null has not made a choice, not made an error."""
    nulled = dict(CLEAN_DESIGN, tube_passes=None, pitch_ratio=None, D_nozzle_hot=None)
    ok, message = env.validate_schema(nulled)
    assert ok, message
    assert env.evaluate("t", TASK, "d", nulled).status == "success"


def test_unknown_fields_are_still_rejected(env):
    ok, _ = env.validate_schema(dict(CLEAN_DESIGN, m_dot_hot=5.0))
    assert not ok


def test_the_reference_design_scores_a_perfect_one(env):
    result = env.evaluate("t", TASK, "clean", CLEAN_DESIGN)
    assert result.status == "success"
    assert result.metrics["num_warnings"] == 0.0
    assert result.score.normalized_total == pytest.approx(1.0)


# ── The nozzle is a lever, not a free win ────────────────────────────

def test_oversized_nozzle_is_rejected_by_drc():
    design = dict(CLEAN_DESIGN, D_nozzle_hot=2.0)
    ok, message = run_heat_exchanger_drc(design)
    assert not ok
    assert "nozzle bore" in message


def test_nozzle_bore_is_capped_relative_to_the_shell():
    shell = CLEAN_DESIGN["outer_shell_di"]
    limit = HeatExchangerSimulator.MAX_NOZZLE_SHELL_RATIO * shell
    assert run_heat_exchanger_drc(dict(CLEAN_DESIGN, D_nozzle_hot=limit * 0.99))[0]
    assert not run_heat_exchanger_drc(dict(CLEAN_DESIGN, D_nozzle_hot=limit * 1.01))[0]


def test_an_oversized_nozzle_costs_mass_and_raises_a_warning():
    """Without this, driving nozzle loss to zero would be free."""
    sim = HeatExchangerSimulator()
    base = {k: v for k, v in CLEAN_DESIGN.items() if not k.startswith("D_nozzle")}
    _, small, _, _ = sim.simulate(dict(base, D_nozzle_hot=0.042, D_nozzle_cold=0.042))
    _, huge, raw, _ = sim.simulate(dict(base, D_nozzle_hot=0.80, D_nozzle_cold=0.80))
    assert huge["mass_total_kg"] > small["mass_total_kg"]
    assert huge["cost_annualised_USD_per_yr"] > small["cost_annualised_USD_per_yr"]
    assert any("oversized nozzle" in w for w in raw["warnings"])


def test_an_undersized_nozzle_still_raises_the_erosion_warning():
    sim = HeatExchangerSimulator()
    base = {k: v for k, v in CLEAN_DESIGN.items() if not k.startswith("D_nozzle")}
    _, _, raw, _ = sim.simulate(dict(base, D_nozzle_hot=0.012, D_nozzle_cold=0.012))
    assert any("nozzle velocity" in w.lower() and "> max" in w for w in raw["warnings"])


# ── The shipped task passes its own audit ────────────────────────────

def test_hard_v3_task_file_is_healthy(env):
    path = os.path.join(os.path.dirname(__file__),
                        "../results/zero_shot/heat_exchanger_hard_v3/task.json")
    with open(path, encoding="utf-8") as handle:
        task = json.load(handle)

    report = env.audit_task(task, num_samples=4000, seed=0)
    assert report.is_healthy(), report.findings
    assert report.forced_warnings == [], "no penalty may be unavoidable"
    assert report.min_warning_count == 0, "a warning-free design must be reachable"
    assert report.craft_reward > report.entry_reward, "engineering must outweigh showing up"
    assert report.physics["target_as_fraction_of_duty_ceiling"] < 0.9


def test_concentric_nozzle_is_bounded_by_the_outer_pipe_not_a_shell_fraction():
    """
    A concentric tube is a pipe, not a shell: a branch cannot exceed the pipe
    it comes off, but the 35% shell rule would be the wrong bound and would
    reject ordinary double-pipe designs.
    """
    design = {
        "geometry_type": "concentric_tube",
        "length": 5.0,
        "inner_tube_di": 0.02,
        "inner_tube_do": 0.025,
        "outer_shell_di": 0.05,
        "number_of_tubes": 1,
        "baffle_spacing": 0.0,
    }
    assert run_heat_exchanger_drc(design)[0], "default nozzle must still fit"
    assert run_heat_exchanger_drc(dict(design, D_nozzle_cold=0.05))[0]
    ok, message = run_heat_exchanger_drc(dict(design, D_nozzle_cold=0.06))
    assert not ok
    assert "outer pipe" in message
