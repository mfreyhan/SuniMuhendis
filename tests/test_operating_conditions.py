"""
Tests for operating conditions as a task parameter.

A heat-exchanger task is not just a set of targets — it is a duty specification:
which streams, how much of them, how hot, how dirty, how strong the vessel. None
of that is a design decision, so none of it belongs in the design schema; but all
of it changes the physics, so a task that cannot set it can only ever pose one
problem. These tests pin that the task can set it, that a design cannot, and that
a malformed task is loud rather than quiet.
"""

import pytest

from sunimuhendis import make_env
from sunimuhendis.environments.heat_exchanger.env import HeatExchangerEnv
from sunimuhendis.environments.heat_exchanger.simulator import HeatExchangerSimulator


TASK = {
    "task_id": "operating_conditions_test",
    "score_version": "heat_exchanger_score_v4",
    "target_heat_duty": 250000.0,
    "max_dp_tube": 10000.0,
    "max_dp_shell": 10000.0,
    "gate_share": 0.30,
    "cost_good": 2000.0,
    "cost_bad": 20000.0,
    "warning_penalty_per_warning": 0.10,
}

DESIGN = {
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


def with_conditions(**conditions):
    return dict(TASK, operating_conditions=conditions)


# ── Defaults are unchanged ───────────────────────────────────────────

def test_a_task_without_operating_conditions_keeps_the_historical_point(env):
    """Every task written before this feature must score exactly as it did."""
    absent = env.evaluate("t", TASK, "d", DESIGN)
    explicit = env.evaluate("t", with_conditions(
        m_dot_hot=HeatExchangerSimulator.DEFAULT_M_DOT_HOT,
        m_dot_cold=HeatExchangerSimulator.DEFAULT_M_DOT_COLD,
        T_hot_in=HeatExchangerSimulator.DEFAULT_T_HOT_IN_C,
        T_cold_in=HeatExchangerSimulator.DEFAULT_T_COLD_IN_C), "d", DESIGN)
    assert absent.metrics["heat_duty_W"] == pytest.approx(explicit.metrics["heat_duty_W"])
    assert absent.score.normalized_total == pytest.approx(explicit.score.normalized_total)


def test_an_empty_block_is_the_same_as_no_block(env):
    assert (env.evaluate("t", with_conditions(), "d", DESIGN).metrics["heat_duty_W"]
            == pytest.approx(env.evaluate("t", TASK, "d", DESIGN).metrics["heat_duty_W"]))


def test_the_default_hook_leaves_the_design_alone():
    """BaseEnvironment's default must not touch anything, for other environments."""
    from sunimuhendis.core.base_environment import BaseEnvironment
    prepared = BaseEnvironment.prepare_simulation_inputs(
        object(), {"a": 1}, {"operating_conditions": {"whatever": 2}})
    assert prepared == {"a": 1}


# ── The task actually moves the physics ──────────────────────────────

def test_raising_the_flow_raises_duty_and_velocity(env):
    base = env.evaluate("t", TASK, "d", DESIGN).metrics
    fast = env.evaluate("t", with_conditions(m_dot_hot=5.0, m_dot_cold=5.0),
                        "d", DESIGN).metrics
    assert fast["heat_duty_W"] > base["heat_duty_W"]
    assert fast["v_tube_m_s"] == pytest.approx(2.0 * base["v_tube_m_s"], rel=1e-6)
    assert fast["dp_tube_Pa"] > base["dp_tube_Pa"]


def test_raising_the_inlet_temperature_raises_duty(env):
    base = env.evaluate("t", TASK, "d", DESIGN).metrics
    hot = env.evaluate("t", with_conditions(T_hot_in=120.0), "d", DESIGN).metrics
    assert hot["heat_duty_W"] > base["heat_duty_W"]


def test_unbalancing_the_flows_raises_the_effectiveness_ceiling(env):
    """
    The reason unbalanced flows matter: the 1-2 shell-and-tube ε ceiling is
    2/(1+Cr+sqrt(1+Cr^2)), so lowering Cr lifts the ceiling and the duty past
    which the F warning becomes unavoidable moves with it.
    """
    balanced = env.analyse_physics(TASK)
    unbalanced = env.analyse_physics(with_conditions(m_dot_hot=2.5, m_dot_cold=12.5))
    assert (unbalanced["epsilon_ceiling_1_2_shell_and_tube"]
            > balanced["epsilon_ceiling_1_2_shell_and_tube"])
    assert (unbalanced["duty_at_F_limit_W"] / unbalanced["duty_ceiling_1_2_shell_and_tube_W"]
            > balanced["duty_at_F_limit_W"] / balanced["duty_ceiling_1_2_shell_and_tube_W"])


def test_analyse_physics_reports_the_point_it_analysed(env):
    physics = env.analyse_physics(with_conditions(m_dot_hot=7.0))
    assert physics["operating_conditions"]["m_dot_hot"] == 7.0
    assert physics["operating_conditions"]["m_dot_cold"] == \
        HeatExchangerSimulator.DEFAULT_M_DOT_COLD


# ── The design cannot choose its own problem ─────────────────────────

def test_a_design_cannot_smuggle_an_operating_condition_through_the_schema(env):
    ok, _ = env.validate_schema(dict(DESIGN, m_dot_hot=0.1))
    assert not ok


def test_the_task_overrides_a_design_that_names_the_same_key(env):
    prepared = env.prepare_simulation_inputs(
        dict(DESIGN, m_dot_hot=0.1), with_conditions(m_dot_hot=5.0))
    assert prepared["m_dot_hot"] == 5.0


# ── A malformed task is loud, not quiet ──────────────────────────────

@pytest.mark.parametrize("conditions", [
    {"m_dot_hot": -1.0},
    {"m_dot_cold": 0.0},
    {"R_fi": -1e-4},
    {"k_wall": 0.0},
    {"m_dot_hot": "fast"},
    {"m_dot_hot": float("inf")},
    {"T_hot_in": 10.0, "T_cold_in": 20.0},
    {"T_cold_in": -300.0},
])
def test_an_impossible_operating_point_raises(env, conditions):
    with pytest.raises(ValueError):
        env.evaluate("t", with_conditions(**conditions), "d", DESIGN)


def test_a_misspelled_key_raises_rather_than_silently_defaulting(env):
    """
    The failure this guards against: 'm_dot_hto' reverting to 2.5 kg/s would
    make every downstream number a quiet lie, and the audit would certify a
    task nobody meant to write.
    """
    with pytest.raises(ValueError, match="unknown operating condition"):
        env.evaluate("t", with_conditions(m_dot_hto=5.0), "d", DESIGN)


def test_a_non_mapping_block_raises(env):
    with pytest.raises(ValueError, match="must be a mapping"):
        env.evaluate("t", dict(TASK, operating_conditions=[1, 2]), "d", DESIGN)


def test_task_misconfiguration_is_not_recorded_as_a_design_failure(env):
    """
    It must raise rather than return status='simulation_error': a typo in a
    task file would otherwise be recorded as every model failing to design,
    indistinguishably from the real thing.
    """
    with pytest.raises(ValueError):
        env.evaluate("t", with_conditions(m_dot_hot=-1.0), "d", DESIGN)


# ── The audit follows the task's operating point ─────────────────────

def test_the_audit_audits_the_point_the_task_specifies(env):
    default = env.audit_task(TASK, num_samples=400, seed=0)
    moved = env.audit_task(with_conditions(m_dot_hot=6.0, m_dot_cold=6.0),
                           num_samples=400, seed=0)
    assert (moved.physics["duty_ceiling_1_2_shell_and_tube_W"]
            > default.physics["duty_ceiling_1_2_shell_and_tube_W"])
    assert moved.warning_frequency != default.warning_frequency
