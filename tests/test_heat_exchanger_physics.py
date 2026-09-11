import json
import math
from pathlib import Path

import ht
import pytest

from sunimuhendis import make_env
from sunimuhendis.environments.heat_exchanger.drc import run_heat_exchanger_drc
from sunimuhendis.environments.heat_exchanger.simulator import HeatExchangerSimulator


ROOT = Path(__file__).resolve().parents[1]


def _design():
    return json.loads(
        (ROOT / "examples/designs/heat_exchanger_valid_001.json").read_text()
    )


def _task():
    return json.loads(
        (ROOT / "configs/tasks/heat_exchanger/task_001.json").read_text()
    )


def test_fixed_operating_conditions_cannot_be_overridden():
    design = dict(_design(), T_hot_in=85.0)
    result = make_env("heat_exchanger").evaluate("task", _task(), "design", design)

    assert result.status == "schema_error"
    assert "Extra inputs are not permitted" in result.error_message


def test_tube_velocity_uses_tubes_per_pass():
    simulator = HeatExchangerSimulator()
    params = simulator._extract_and_validate_params(_design())
    tube = simulator._calc_tube_side(
        params["geo"], params["di"], params["do"], params["L"],
        params["N_tubes"], params["N_pass"], params["hot"],
        params["wall"], params["mech"],
    )

    expected_tubes_per_pass = params["N_tubes"] / params["N_pass"]
    expected_area = (
        expected_tubes_per_pass * math.pi * (params["di"] / 2.0) ** 2
    )
    expected_velocity = params["hot"]["m_dot"] / (
        params["hot"]["rho"] * expected_area
    )

    assert tube["tubes_per_pass"] == expected_tubes_per_pass
    assert tube["v"] == pytest.approx(expected_velocity)


def test_lmtd_factor_matches_ht_reference():
    result = make_env("heat_exchanger").evaluate(
        "task", _task(), "design", _design()
    )
    metrics = result.metrics
    expected = ht.F_LMTD_Fakheri(
        Thi=80.0,
        Tho=metrics["t_hot_out_C"],
        Tci=20.0,
        Tco=metrics["t_cold_out_C"],
        shells=1,
    )

    assert result.status == "success"
    assert metrics["F_LMTD"] == pytest.approx(expected)
    assert metrics["F_LMTD"] > 0.0


def test_impossible_tube_bundle_fails_drc():
    design = dict(_design(), outer_shell_di=0.4, number_of_tubes=152)

    valid, error = run_heat_exchanger_drc(design)

    assert valid is False
    assert "Tube bundle diameter" in error


def test_triangular_pitch_has_positive_equivalent_diameter():
    design = dict(_design(), outer_shell_di=0.5, pitch_type="triangular")

    success, metrics, _, error = HeatExchangerSimulator().simulate(design)

    assert success, error
    assert metrics["Re_shell"] > 0.0
    assert metrics["h_o_W_m2K"] > 0.0


def test_concentric_tube_has_one_pass_no_baffles_and_nozzle_loss():
    design = {
        "geometry_type": "concentric_tube",
        "length": 5.0,
        "inner_tube_di": 0.02,
        "inner_tube_do": 0.025,
        "outer_shell_di": 0.05,
        "number_of_tubes": 1,
        "baffle_spacing": 0.0,
    }

    success, metrics, _, error = HeatExchangerSimulator().simulate(design)

    assert success, error
    assert metrics["tube_passes"] == 1
    assert metrics["baffle_count"] == 0
    assert metrics["dp_shell_nozzle_Pa"] > 0.0
    assert metrics["vibration_applicable"] == 0.0


def test_vibration_limit_responds_to_unsupported_span():
    simulator = HeatExchangerSimulator()
    params = simulator._extract_and_validate_params(_design())

    short_span = simulator._calc_mechanical(
        params["geo"], params["di"], params["do"], params["D_shell"],
        params["L"], 0.3, params["N_tubes"], 0.5,
        params["hot"]["rho"], params["cold"]["rho"],
        params["material"], params["mech"],
    )
    long_span = simulator._calc_mechanical(
        params["geo"], params["di"], params["do"], params["D_shell"],
        params["L"], 1.2, params["N_tubes"], 0.5,
        params["hot"]["rho"], params["cold"]["rho"],
        params["material"], params["mech"],
    )

    assert short_span["natural_frequency_Hz"] > long_span["natural_frequency_Hz"]
    assert short_span["v_critical_vibration"] > long_span["v_critical_vibration"]
    assert short_span["mass_damping_parameter"] > 0.0
