"""
Tests for the simulator V4 corrections.

Each test pins one defect found by the physics audit
(``reports/simulator_v3_physics_audit.md``).
"""

import math

import pytest

from sunimuhendis.environments.heat_exchanger.drc import run_heat_exchanger_drc
from sunimuhendis.environments.heat_exchanger.simulator import HeatExchangerSimulator


BASE_DESIGN = {
    "geometry_type": "shell_and_tube",
    "length": 5.0,
    "inner_tube_di": 0.016,
    "inner_tube_do": 0.02,
    "outer_shell_di": 0.48,
    "number_of_tubes": 200,
    "baffle_spacing": 0.5,
}


@pytest.fixture(scope="module")
def sim():
    return HeatExchangerSimulator()


def simulate(sim, **overrides):
    design = dict(BASE_DESIGN)
    design.update(overrides)
    success, metrics, raw, error = sim.simulate(design)
    assert success, "simulation failed: {}".format(error)
    return metrics, raw


def test_version_is_v4(sim):
    """Outputs changed, so results from V3 and V4 must not be pooled."""
    assert sim.VERSION == "v4"


# ── DRC agrees with the simulator about layout (audit 5.5) ───────────

def test_drc_rejects_tube_count_not_divisible_by_the_designs_own_passes():
    """Previously DRC assumed two passes, so this passed DRC then failed to simulate."""
    design = dict(BASE_DESIGN, tube_passes=4, number_of_tubes=6)
    ok, message = run_heat_exchanger_drc(design)
    assert not ok
    assert "tube passes" in message


def test_drc_and_simulator_agree_on_a_valid_four_pass_design(sim):
    design = dict(BASE_DESIGN, tube_passes=4, number_of_tubes=8, outer_shell_di=0.3)
    drc_ok, message = run_heat_exchanger_drc(design)
    assert drc_ok, message
    success, _, _, error = sim.simulate(design)
    assert success, error


def test_drc_rejects_odd_tube_passes():
    ok, message = run_heat_exchanger_drc(dict(BASE_DESIGN, tube_passes=3, number_of_tubes=9))
    assert not ok
    assert "even" in message


def test_drc_enforces_tema_minimum_pitch_ratio():
    ok, message = run_heat_exchanger_drc(dict(BASE_DESIGN, pitch_ratio=1.1))
    assert not ok
    assert "1.25" in message


def test_drc_rejects_unknown_pitch_type():
    ok, message = run_heat_exchanger_drc(dict(BASE_DESIGN, pitch_type="hexagonal"))
    assert not ok
    assert "pitch type" in message.lower()


def test_drc_still_accepts_a_plain_seven_field_design():
    ok, message = run_heat_exchanger_drc(BASE_DESIGN)
    assert ok, message


# ── Unsupported span follows TEMA, not one flat number (audit 5.x) ───

def test_span_limit_rises_with_tube_diameter():
    limits = [HeatExchangerSimulator.max_unsupported_span(od)
              for od, _ in HeatExchangerSimulator.TEMA_MAX_UNSUPPORTED_SPAN]
    assert limits == sorted(limits)
    assert limits[0] < limits[-1]


def test_span_limit_is_conservative_between_table_entries():
    """A diameter between entries takes the smaller entry's limit."""
    half_inch = HeatExchangerSimulator.max_unsupported_span(0.0127)
    between = HeatExchangerSimulator.max_unsupported_span(0.014)
    assert between == half_inch


def test_span_limit_clamps_outside_the_table():
    table = HeatExchangerSimulator.TEMA_MAX_UNSUPPORTED_SPAN
    assert HeatExchangerSimulator.max_unsupported_span(0.001) == table[0][1]
    assert HeatExchangerSimulator.max_unsupported_span(1.0) == table[-1][1]


def test_small_tube_now_warns_at_a_span_the_flat_limit_allowed(sim):
    """
    A 1/2" tube on a 1.3 m span: inside the old flat 1.5 m limit, outside the
    1.118 m TEMA limit for that diameter.
    """
    metrics, raw = simulate(
        sim, inner_tube_do=0.0127, inner_tube_di=0.0105,
        number_of_tubes=100, outer_shell_di=0.3, baffle_spacing=1.3, length=5.0,
    )
    assert metrics["max_unsupported_span_m"] == pytest.approx(1.118)
    assert metrics["span_ok"] == 0.0
    assert any("Unsupported span" in w for w in raw["warnings"])


def test_large_tube_tolerates_a_span_the_flat_limit_rejected(sim):
    """A 2" tube may span 3.0 m — beyond the old flat 1.5 m limit."""
    metrics, _ = simulate(
        sim, inner_tube_do=0.0508, inner_tube_di=0.042,
        number_of_tubes=20, outer_shell_di=0.5, baffle_spacing=3.0, length=8.0,
    )
    assert metrics["max_unsupported_span_m"] == pytest.approx(3.175)
    assert metrics["span_ok"] == 1.0


def test_span_check_is_not_applied_to_a_concentric_tube(sim):
    metrics, _ = simulate(
        sim, geometry_type="concentric_tube", number_of_tubes=1,
        inner_tube_di=0.02, inner_tube_do=0.025, outer_shell_di=0.05,
        length=5.0, baffle_spacing=1.0,
    )
    assert metrics["span_ok"] == 1.0
    assert math.isfinite(metrics["max_unsupported_span_m"])


# ── ASME wall thickness uses the code formula (audit 5.b) ────────────

def test_shell_thickness_minimum_matches_asme_ug27():
    """t = P·R/(S·E − 0.6·P) — note the MINUS the earlier form got wrong."""
    sim = HeatExchangerSimulator()
    pressure, stress, shell_id = 5.0e6, 137e6, 0.48
    _, metrics, _, error = sim.simulate(
        dict(BASE_DESIGN, P_design=pressure, allowable_stress=stress)
    )
    expected = pressure * (shell_id / 2.0) / (stress * 1.0 - 0.6 * pressure)
    assert metrics["shell_thickness_min_mm"] == pytest.approx(expected * 1000)


def test_asme_formula_is_more_conservative_than_the_old_one_at_pressure():
    """The old form added 0.4P where the code subtracts 0.6P, understating t."""
    pressure, stress, shell_id = 2.0e7, 137e6, 0.5
    corrected = pressure * (shell_id / 2.0) / (stress - 0.6 * pressure)
    previous = pressure * shell_id / (2.0 * stress + 0.4 * pressure)
    assert corrected > previous


def test_joint_efficiency_increases_required_thickness(sim):
    _, strong, _, _ = sim.simulate(dict(BASE_DESIGN, P_design=5.0e6, joint_efficiency=1.0))
    _, weak, _, _ = sim.simulate(dict(BASE_DESIGN, P_design=5.0e6, joint_efficiency=0.7))
    assert weak["shell_thickness_min_mm"] > strong["shell_thickness_min_mm"]


def test_invalid_joint_efficiency_is_rejected(sim):
    success, _, _, _ = sim.simulate(dict(BASE_DESIGN, joint_efficiency=1.5))
    assert not success


# ── Correlation limits are reported, not charged to the design ───────

def test_low_shell_reynolds_is_flagged_without_adding_a_warning(sim):
    """
    The reference design runs at Re_shell ≈ 1000, below Kern's validity floor.
    That is the simulator's limitation, so it must not cost the design score.
    """
    metrics, raw = simulate(sim)
    assert metrics["Re_shell"] < HeatExchangerSimulator.KERN_RE_VALID_MIN
    assert metrics["shell_correlation_in_range"] == 0.0
    assert any("validity floor" in note for note in raw["fidelity_notes"])
    # The note is not a warning, so num_warnings does not count it.
    assert metrics["num_warnings"] == float(len(raw["warnings"]))
    assert not any("validity" in w for w in raw["warnings"])


def test_sparse_bundle_in_a_wide_shell_is_flagged(sim):
    metrics, raw = simulate(sim, number_of_tubes=10, outer_shell_di=1.0)
    assert metrics["bundle_fill_fraction"] < 0.7
    assert any("fills only" in note for note in raw["fidelity_notes"])
    assert not any("fills only" in w for w in raw["warnings"])


def test_fidelity_notes_are_present_for_every_successful_simulation(sim):
    _, raw = simulate(sim)
    assert "fidelity_notes" in raw
    assert isinstance(raw["fidelity_notes"], list)


# ── Determinism survives the changes ─────────────────────────────────

def test_simulation_remains_deterministic(sim):
    first = sim.simulate(dict(BASE_DESIGN))
    second = sim.simulate(dict(BASE_DESIGN))
    assert first[1] == second[1]
