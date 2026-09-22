"""Adapter-equivalence case for the pinned NASA OptTurb example.

Reference values were produced by executing
``examples/optturb-turbine/optturb-fixed_pressure_loss2.py`` directly at NASA
turbo-design commit 23c2b0bf781b4b030014f458ecfde872896777a2 with moving
streamlines disabled. This validates translation, not experimental physics.
"""
import contextlib
import io
import pytest

from scripts.run_throughflow import build_case
from scripts.run_throughflow_compressor import build_case as build_compressor_case
from scripts.run_throughflow_resolution_study import run_study
from sunimuhendis import make_env

REFERENCE={"power_W":3394088.5080275447,"pressure_ratio_total":3.38544143180728,"efficiency_polytropic":0.732031028534128}
COMPRESSOR_REFERENCE={"power_W":527700.3258916077,"pressure_ratio_total":1.322718069014324,"efficiency_polytropic":1.0078571383675168}
MULTISTAGE_COMPRESSOR_REFERENCE={"power_W":1015399.9329846853,"pressure_ratio_total":1.6858229801093048,"efficiency_polytropic":1.0160254361581715}

def test_optturb_adapter_matches_direct_upstream_solve():
    pytest.importorskip("turbodesign")
    design,task=build_case(1,streamtubes=2)
    with contextlib.redirect_stdout(io.StringIO()):
        result=make_env("turbomachinery_throughflow").evaluate("validation",task,"optturb",design)
    assert result.status=="success"
    for name,expected in REFERENCE.items():
        assert result.metrics[name]==pytest.approx(expected,rel=1e-12,abs=1e-9)
    assert result.metrics["stage_count"]==1.0
    assert result.metrics["streamline_count"]==3.0
    assert result.raw_simulation_output["physics_profile"]["profile_id"]=="optturb_turbine_regression_v1"
    assert result.raw_simulation_output["physics_profile"]["backend_revision"]=="23c2b0bf781b4b030014f458ecfde872896777a2"
    assert result.score.normalized_total==0.0

def test_two_stage_compressor_with_ten_streamtubes_is_deterministic():
    pytest.importorskip("turbodesign")
    design,task=build_compressor_case(stages=2,streamtubes=10)
    results=[]
    for _ in range(2):
        with contextlib.redirect_stdout(io.StringIO()):
            results.append(make_env("turbomachinery_throughflow").evaluate("validation",task,"compressor_2_stage",design))
    for result in results:
        assert result.status=="success"
        for name,expected in MULTISTAGE_COMPRESSOR_REFERENCE.items():
            assert result.metrics[name]==pytest.approx(expected,rel=1e-12,abs=1e-9)
        assert result.metrics["stage_count"]==2.0
        assert result.metrics["streamline_count"]==11.0
        assert result.metrics["streamtube_count"]==10.0
        assert len(result.raw_simulation_output["rows"])==4
        assert all(len(row["P0"])==11 for row in result.raw_simulation_output["rows"])
        assert all(len(row["metal_angle_in_deg"])==11 for row in result.raw_simulation_output["rows"])
        assert all(len(row["metal_angle_out_deg"])==11 for row in result.raw_simulation_output["rows"])
    assert results[0].metrics==results[1].metrics
    assert results[0].raw_simulation_output["rows"]==results[1].raw_simulation_output["rows"]

def test_ten_streamtube_resolution_gap_is_reported_for_the_regression_case():
    pytest.importorskip("turbodesign")
    with contextlib.redirect_stdout(io.StringIO()):
        report=run_study(stages=2,streamtube_counts=[10,20])
    assert report["physical_validation"] is False
    coarse=report["observations"][0]
    assert coarse["status"]=="success"
    differences=coarse["relative_difference_to_finest"]
    assert differences["power_W"]==pytest.approx(.019909017063272257,rel=1e-10)
    assert differences["pressure_ratio_total"]==pytest.approx(.006891053746261644,rel=1e-10)
    assert differences["efficiency_polytropic"]==pytest.approx(.0008776453243097311,rel=1e-10)

def test_all_eleven_metal_angle_values_reach_the_nasa_rows_without_resampling():
    pytest.importorskip("turbodesign")
    design,task=build_compressor_case(stages=1,streamtubes=10)
    rotor_in=[float(index) for index in range(11)]
    rotor_out=[-24.0+0.1*index for index in range(11)]
    design["rows"][1]["metal_angle_in_deg"]=rotor_in
    design["rows"][1]["metal_angle_out_deg"]=rotor_out
    with contextlib.redirect_stdout(io.StringIO()):
        result=make_env("turbomachinery_throughflow").evaluate("validation",task,"radial_angles",design)
    assert result.status=="success"
    nasa_rotor=result.raw_simulation_output["rows"][0]
    assert nasa_rotor["metal_angle_in_deg"]==pytest.approx(rotor_in)
    assert nasa_rotor["metal_angle_out_deg"]==pytest.approx(rotor_out)

def test_mattingly_compressor_adapter_matches_direct_upstream_solve():
    pytest.importorskip("turbodesign")
    design,task=build_compressor_case(streamtubes=2)
    with contextlib.redirect_stdout(io.StringIO()):
        result=make_env("turbomachinery_throughflow").evaluate("validation",task,"mattingly_9_1",design)
    assert result.status=="success"
    for name,expected in COMPRESSOR_REFERENCE.items():
        assert result.metrics[name]==pytest.approx(expected,rel=1e-12,abs=1e-9)
    assert result.metrics["stage_count"]==1.0
    assert result.metrics["streamline_count"]==3.0
    assert result.metrics["efficiency_polytropic"]>1.0
    assert result.score.normalized_total==0.0
