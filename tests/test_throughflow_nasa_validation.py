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
from sunimuhendis import make_env

REFERENCE={"power_W":3394088.5080275447,"pressure_ratio_total":3.38544143180728,"efficiency_polytropic":0.732031028534128}
COMPRESSOR_REFERENCE={"power_W":527700.3258916077,"pressure_ratio_total":1.322718069014324,"efficiency_polytropic":1.0078571383675168}

def test_optturb_adapter_matches_direct_upstream_solve():
    pytest.importorskip("turbodesign")
    design,task=build_case(1)
    with contextlib.redirect_stdout(io.StringIO()):
        result=make_env("turbomachinery_throughflow").evaluate("validation",task,"optturb",design)
    assert result.status=="success"
    for name,expected in REFERENCE.items():
        assert result.metrics[name]==pytest.approx(expected,rel=1e-12,abs=1e-9)
    assert result.metrics["stage_count"]==1.0
    assert result.metrics["streamline_count"]==3.0
    assert result.score.normalized_total==0.0

def test_mattingly_compressor_adapter_matches_direct_upstream_solve():
    pytest.importorskip("turbodesign")
    design,task=build_compressor_case()
    with contextlib.redirect_stdout(io.StringIO()):
        result=make_env("turbomachinery_throughflow").evaluate("validation",task,"mattingly_9_1",design)
    assert result.status=="success"
    for name,expected in COMPRESSOR_REFERENCE.items():
        assert result.metrics[name]==pytest.approx(expected,rel=1e-12,abs=1e-9)
    assert result.metrics["stage_count"]==1.0
    assert result.metrics["streamline_count"]==3.0
    assert result.metrics["efficiency_polytropic"]>1.0
    assert result.score.normalized_total==0.0
