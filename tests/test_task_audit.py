"""Tests for the task feasibility audit (BaseEnvironment.audit_task)."""

import pytest

from sunimuhendis import make_env
from sunimuhendis.core.base_environment import BaseEnvironment
from sunimuhendis.core.base_score import BaseScoreFunction
from sunimuhendis.core.base_simulator import BaseSimulator
from sunimuhendis.core.types import Requirement, ScoreResult


SAMPLES = 3000

# The task that this repo's audit was written against: a duty target sitting at
# 95% of the configuration's ε ceiling, and a pressure-drop limit two thirds
# consumed by nozzle loss the schema does not expose.
WALLED_TASK = {
    "task_id": "audit_walled",
    "score_version": "heat_exchanger_score_v3",
    "target_heat_duty": 350000.0,
    "max_dp_tube": 2500.0,
    "max_dp_shell": 2500.0,
}

# A task with real headroom: well below the ε ceiling, with a pressure-drop
# budget the design actually controls.
ROOMY_TASK = {
    "task_id": "audit_roomy",
    "score_version": "heat_exchanger_score_v3",
    "target_heat_duty": 150000.0,
    "max_dp_tube": 50000.0,
    "max_dp_shell": 50000.0,
}


@pytest.fixture(scope="module")
def env():
    return make_env("heat_exchanger", score_version="heat_exchanger_score_v3")


@pytest.fixture(scope="module")
def walled_report(env):
    return env.audit_task(WALLED_TASK, num_samples=SAMPLES, seed=0)


@pytest.fixture(scope="module")
def roomy_report(env):
    return env.audit_task(ROOMY_TASK, num_samples=SAMPLES, seed=0)


# ── Requirement semantics ────────────────────────────────────────────

def test_requirement_gte_and_lte():
    at_least = Requirement(name="duty", metric_key="q", operator="gte", limit=100.0)
    assert at_least.satisfied_by({"q": 100.0})
    assert at_least.satisfied_by({"q": 150.0})
    assert not at_least.satisfied_by({"q": 99.0})

    at_most = Requirement(name="drop", metric_key="dp", operator="lte", limit=100.0)
    assert at_most.satisfied_by({"dp": 100.0})
    assert not at_most.satisfied_by({"dp": 101.0})


def test_requirement_missing_or_non_numeric_metric_is_not_satisfied():
    req = Requirement(name="duty", metric_key="q", operator="gte", limit=100.0)
    assert not req.satisfied_by({})
    assert not req.satisfied_by({"q": None})
    assert not req.satisfied_by({"q": "200"})
    # bool is an int subclass, but a flag is not a measurement
    assert not req.satisfied_by({"q": True})


# ── Hooks are optional, and say so ───────────────────────────────────

class _NullSimulator(BaseSimulator):
    def simulate(self, design_params):
        return True, {}, {}, ""


class _NullScore(BaseScoreFunction):
    def calculate_score(self, task_params, metrics, is_valid=True, error_message=None):
        return ScoreResult(normalized_total=0.0, is_valid=is_valid, error_message=error_message)


class _UnauditableEnv(BaseEnvironment):
    def validate_schema(self, design_params):
        return True, None

    def run_drc(self, design_params):
        return True, None


def test_environment_without_hooks_cannot_be_audited():
    """An environment that has not opted in fails with a message naming the hook."""
    env = _UnauditableEnv(_NullSimulator(), _NullScore())
    with pytest.raises(NotImplementedError, match="sample_designs"):
        env.audit_task({})


def test_warning_normalisation_collapses_numbers():
    collapse = BaseEnvironment.normalise_warning
    assert (collapse("Tube velocity 0.13 m/s < min 0.5 m/s (fouling risk)")
            == collapse("Tube velocity 0.31 m/s < min 0.5 m/s (fouling risk)"))


# ── Sampling ─────────────────────────────────────────────────────────

def test_sample_designs_is_deterministic(env):
    assert env.sample_designs(50, seed=7) == env.sample_designs(50, seed=7)
    assert env.sample_designs(50, seed=7) != env.sample_designs(50, seed=8)


def test_sample_designs_covers_both_geometries(env):
    kinds = {d["geometry_type"] for d in env.sample_designs(500, seed=0)}
    assert kinds == {"shell_and_tube", "concentric_tube"}


def test_audit_is_deterministic(env):
    first = env.audit_task(ROOMY_TASK, num_samples=400, seed=3)
    second = env.audit_task(ROOMY_TASK, num_samples=400, seed=3)
    assert first.model_dump() == second.model_dump()


# ── The audit finds the walls it was written to find ─────────────────

def test_walled_task_is_reported_unhealthy(walled_report):
    assert not walled_report.is_healthy()
    assert walled_report.feasible_count > 0, "task is reachable, just badly calibrated"


def test_walled_task_duty_sits_against_the_epsilon_ceiling(walled_report):
    physics = walled_report.physics
    assert physics["target_as_fraction_of_duty_ceiling"] > 0.9
    assert "CRITICAL_duty_near_ceiling" in physics


def test_walled_task_forces_unavoidable_warnings(walled_report):
    """Both mechanisms are proven in closed form, and sampling agrees."""
    assert "CRITICAL_F_warning_forced" in walled_report.physics
    assert "CRITICAL_tube_velocity_warning_forced" in walled_report.physics
    # No feasible design is warning-free, and the tube-velocity warning is
    # common to every one of them.
    assert walled_report.min_warning_count >= 2
    assert any("fouling risk" in w for w in walled_report.forced_warnings)


def test_walled_task_pressure_budget_is_mostly_beyond_the_designers_reach(walled_report):
    assert walled_report.physics["tube_nozzle_share_of_limit"] > 0.5
    assert "WARNING_tube_budget_is_fixed" in walled_report.physics


# ── …and does not cry wolf on a task with headroom ───────────────────

def test_roomy_task_has_no_forced_penalty(roomy_report):
    assert roomy_report.forced_warnings == []
    assert "CRITICAL_F_warning_forced" not in roomy_report.physics
    assert "CRITICAL_tube_velocity_warning_forced" not in roomy_report.physics
    assert "CRITICAL_duty_near_ceiling" not in roomy_report.physics


def test_roomy_task_leaves_the_pressure_budget_to_the_design(roomy_report):
    assert roomy_report.physics["tube_nozzle_share_of_limit"] < 0.1
    assert roomy_report.physics["tube_velocity_cap_m_s"] > 0.5


def test_roomy_task_is_reachable(roomy_report):
    assert roomy_report.feasible_count > 0
    assert roomy_report.score_ceiling > roomy_report.feasible_score_floor


# ── Reporting surface ────────────────────────────────────────────────

def test_report_records_per_requirement_satisfaction(walled_report):
    names = set(walled_report.requirement_satisfaction)
    assert names == {"heat duty", "tube pressure drop", "shell pressure drop"}
    assert all(0.0 <= v <= 1.0 for v in walled_report.requirement_satisfaction.values())


def test_report_identifies_checks_that_never_fire(walled_report):
    """The ASME thickness checks cannot fire at the default atmospheric design pressure."""
    dead = " ".join(walled_report.dead_checks)
    assert "Tube wall" in dead and "Shell wall" in dead


def test_summary_is_printable(walled_report):
    text = walled_report.summary()
    assert "Task feasibility audit" in text
    assert "findings:" in text
