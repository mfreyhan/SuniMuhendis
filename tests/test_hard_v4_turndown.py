"""
Tests for multi-point evaluation and the heat_exchanger_hard_v4 task.

hard_v4 exists because hard_v3 could be solved by satisfying three constraints
out of eighteen. Measured over its own gate-passing designs, eleven of hard_v3's
declared limits never came within 15% of binding: both pressure limits ran at
27% and 19% of budget, shell velocity at 3.6%, vibration at 2.5%. With thirteen
design variables against three binding constraints the problem is under-
determined, and a design can satisfy it while leaving everything else slack.

Sweeping the operating point does not fix that — flow, inlet temperature and
capacity ratio were each measured and none lifted the count above three of
fourteen. Requiring the same design to work at a second load does: of the ten
sampled designs that met every requirement at full load with no warnings at
all, ten raised at least one at reduced flow. Velocity has a floor for fouling
and a ceiling for erosion, so one design cannot be sized for one flow.
"""

import json
import os

import pytest

from sunimuhendis import make_env


HERE = os.path.dirname(__file__)
TASK_PATH = os.path.join(HERE, "../results/zero_shot/heat_exchanger_hard_v4/task.json")


@pytest.fixture(scope="module")
def env():
    return make_env("heat_exchanger", score_version="heat_exchanger_score_v4")


@pytest.fixture(scope="module")
def task():
    with open(TASK_PATH, encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def witness(task):
    return task["reference_designs"][0]


def single_point(task):
    """The same task with the turndown requirement removed."""
    return {k: v for k, v in task.items() if k != "secondary_operating_points"}


# ── The second load is evaluated, and it counts ──────────────────────

def test_the_turndown_point_is_simulated(env, task, witness):
    result = env.evaluate("t", task, "w", witness)
    points = result.raw_simulation_output["secondary_points"]
    assert "turndown" in points
    turndown = points["turndown"]["metrics"]
    assert turndown["heat_duty_W"] < result.metrics["heat_duty_W"]
    assert turndown["v_tube_m_s"] == pytest.approx(0.70 * result.metrics["v_tube_m_s"], rel=1e-6)


def test_warnings_from_both_loads_are_summed(env, task):
    """A design clean at full load and dirty at turndown must be charged for it."""
    sized_for_one_load = dict(task["reference_designs"][0], number_of_tubes=120)
    full_only = env.evaluate("t", single_point(task), "d", sized_for_one_load)
    both = env.evaluate("t", task, "d", sized_for_one_load)
    assert both.metrics["num_warnings"] > full_only.metrics["num_warnings"]
    assert both.metrics["turndown_num_warnings"] > 0
    assert both.score.normalized_total < full_only.score.normalized_total


def test_turndown_warnings_are_labelled_by_their_load(env, task):
    result = env.evaluate("t", task, "d",
                          dict(task["reference_designs"][0], number_of_tubes=120))
    assert any(w.startswith("[turndown]") for w in result.raw_simulation_output["warnings"])


def test_the_gate_is_still_a_single_load(env, task):
    """
    Entry cost must not rise: the requirements stay a full-load gate, so
    reaching 0.30 is exactly as hard as it was. Only quality got harder.
    """
    for design in env.sample_designs(400, seed=3, task_params=task)[:400]:
        if not env.validate_schema(design)[0]:
            continue
        one = env.evaluate("t", single_point(task), "d", design)
        two = env.evaluate("t", task, "d", design)
        if one.status == "success" and two.status == "success":
            assert (one.score.components["gate_passed"]
                    == two.score.components["gate_passed"])


# ── The task is certified, not asserted ──────────────────────────────

def test_the_witness_scores_a_perfect_one(env, task, witness):
    """
    Sampling can show a score is reachable and never that it is not, so the
    task's ceiling rests on this design rather than on the audit.
    """
    result = env.evaluate("t", task, "witness", witness)
    assert result.status == "success"
    assert result.metrics["num_warnings"] == 0.0
    assert result.score.normalized_total == pytest.approx(1.0)


def test_the_witness_is_clean_at_both_loads(env, task, witness):
    result = env.evaluate("t", task, "witness", witness)
    assert result.metrics["turndown_num_warnings"] == 0.0
    assert result.raw_simulation_output["warnings"] == []


def test_hard_v4_passes_its_own_audit(env, task):
    report = env.audit_task(task, num_samples=4000, seed=0)
    assert report.is_healthy(), report.findings
    assert report.forced_warnings == [], "no penalty may be unavoidable"
    assert report.reference_failures == [], report.reference_failures
    assert report.craft_reward > report.entry_reward, "engineering must outweigh showing up"
    assert report.score_ceiling == pytest.approx(1.0)


def test_a_witness_that_does_not_hold_is_a_critical_finding(env, task):
    """A feasibility claim backed by a design that fails is worse than none."""
    broken = dict(task, reference_designs=[
        dict(task["reference_designs"][0], number_of_tubes=4)])
    report = env.audit_task(broken, num_samples=200, seed=0)
    assert report.reference_failures
    assert not report.is_healthy()
    assert any(f.startswith("CRITICAL") and "reference design" in f for f in report.findings)


def test_turndown_below_the_feasible_range_is_caught_as_a_wall(env, task):
    """
    The turndown depth is a dial, and it has a bottom. At 40% of full flow
    every feasible design trips the tube-velocity floor: 40% turndown means
    full-load velocity must exceed 1.25 m/s, and the tube count that buys
    that velocity cannot also buy the area the duty target needs inside the
    pressure budget. That is the hard_v2 pathology — a penalty no design can
    avoid — and the audit must say so rather than let it ship. 70% was chosen
    because a design reaching a perfect score there is exhibited, not assumed.
    """
    too_deep = dict(task, reference_designs=[], secondary_operating_points=[
        {"name": "turndown", "operating_conditions": {"m_dot_hot": 1.0, "m_dot_cold": 1.0}}])
    report = env.audit_task(too_deep, num_samples=4000, seed=0)
    assert report.forced_warnings, "a forced warning at 50% turndown must be reported"
    assert not report.is_healthy()


# ── Task configuration is validated ──────────────────────────────────

@pytest.mark.parametrize("points", [
    [{"name": "turndown"}],
    [{"name": "turndown", "operating_conditions": {}}],
    [{"name": "a", "operating_conditions": {"m_dot_hot": 1.0}},
     {"name": "a", "operating_conditions": {"m_dot_hot": 2.0}}],
    [{"name": "turndown", "operating_conditions": {"m_dot_hot": -1.0}}],
    [{"name": "turndown", "operating_conditions": {"m_dot_hto": 1.0}}],
    [{"name": "turndown", "operating_conditions": {"m_dot_hot": 1.0}, "extra": 1}],
    ["not a mapping"],
])
def test_a_malformed_secondary_point_raises(env, task, witness, points):
    with pytest.raises(ValueError):
        env.evaluate("t", dict(task, secondary_operating_points=points), "w", witness)


def test_a_secondary_point_inherits_what_it_does_not_change(env, task, witness):
    """A turndown case names the flows it changes, not the whole operating point."""
    inherited = dict(task, operating_conditions={"m_dot_hot": 2.5, "m_dot_cold": 2.5,
                                                 "T_hot_in": 95.0, "T_cold_in": 20.0})
    _, inputs = env.secondary_simulations(witness, inherited)[0]
    assert inputs["T_hot_in"] == 95.0
    assert inputs["m_dot_hot"] == 1.75


def test_a_task_without_secondary_points_is_unaffected(env, task, witness):
    one = env.evaluate("t", single_point(task), "w", witness)
    assert "secondary_points" not in one.raw_simulation_output
    assert "turndown_num_warnings" not in one.metrics
