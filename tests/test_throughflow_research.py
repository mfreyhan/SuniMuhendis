"""Tests for the research instrumentation, not for future throughflow physics."""
import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('throughflow_probe', ROOT / 'scripts/throughflow_research/probe_backend.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_research_case_identifiers_are_unique():
    cases = probe.cases()
    assert len({c['id'] for c in cases}) == len(cases)


def test_no_resolution_override_preserves_constructor_input():
    original = ast.parse('spool = TurbineSpool(num_streamlines=7)')
    transformed = probe.Instrument(None, None).visit(ast.parse('spool = TurbineSpool(num_streamlines=7)'))
    assert ast.dump(original) == ast.dump(transformed)


def test_resolution_override_does_not_touch_blade_angles():
    source = 'row.metal_exit_angle = [61, 63, 65]\nspool = TurbineSpool(num_streamlines=3)'
    transformed = probe.Instrument(9, None).visit(ast.parse(source))
    assert ast.dump(transformed.body[0]) == ast.dump(ast.parse(source).body[0])
    constructor = transformed.body[1].value
    assert [k.value.value for k in constructor.keywords if k.arg == 'num_streamlines'] == [9]


def test_plots_are_removed_but_physics_and_solve_order_are_preserved():
    tree = ast.fix_missing_locations(probe.Instrument(None, None).visit(ast.parse('spool.solve()\nspool.plot()\nanswer = 2 * 3')))
    calls = []
    def solve(obj, method):
        calls.append((obj, method))
    marker = object()
    namespace = {'spool': marker, '_probe_solve': solve}
    exec(compile(tree, '<probe-test>', 'exec'), namespace)
    assert calls == [(marker, 'solve')]
    assert namespace['answer'] == 6


def test_upstream_source_remains_separate_from_package():
    assert not any((ROOT / 'src').rglob('turbine_spool.py'))
