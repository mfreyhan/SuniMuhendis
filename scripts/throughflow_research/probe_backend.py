"""Run pinned upstream examples with recorded research-only interventions.

No NASA source or geometry is copied into this repository. The original example
is loaded from the separately cloned, pinned checkout. Plot/export calls are
suppressed in memory. Solver math is not patched. A completed solve is NOT a
claim of convergence, physical validation or support in SuniMuhendis.
"""
import argparse
import ast
import contextlib
import hashlib
import io
import importlib.metadata as metadata
import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
import traceback
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "build/throughflow_research/turbo-design"
REPORTS = ROOT / "reports/throughflow_phase_0_2"
PIN = "23c2b0bf781b4b030014f458ecfde872896777a2"
EXAMPLES = {
    "turbine1": "optturb-turbine/optturb-fixed_pressure_loss2.py",
    "turbine2": "optturb-multistage/multistage-fixed_pressure_loss2.py",
    "compressor1": "mattingly-axial-compressor/example9.1.py",
    "compressor10": "EEE-HPC/eee-hpc.py",
    "radial": "radial-turbine/radial_turbine-1D.py",
    "eee_hpt": "EEE-HPT/eee_hpt.py",
}


def sanitize(value):
    import numpy as np
    if isinstance(value, dict):
        return {str(k): sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(v) for v in value]
    if isinstance(value, np.ndarray):
        return sanitize(value.tolist())
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else str(value)
    if isinstance(value, np.integer):
        return int(value)
    return value


def snapshot(spool):
    import numpy as np
    rows = []
    for r in spool.rows:
        entry = {"type": r.row_type.name, "stage_id": r.stage_id,
                 "loss_model": type(r.loss_function).__name__}
        for key in ("r", "P0", "T0", "P", "T", "M", "M_rel", "Yp", "power",
                    "total_massflow", "total_massflow_no_coolant", "massflow", "rpm",
                    "metal_exit_angle", "alpha2", "beta2", "axial_chord", "chord"):
            entry[key] = sanitize(getattr(r, key, None))
        rows.append(entry)
    mass = np.array([r.total_massflow_no_coolant for r in spool.rows], dtype=float)
    fields = [np.asarray(getattr(r, key), dtype=float) for r in spool.rows for key in ("P0", "T0", "P", "T", "M", "Yp")]
    finite = bool(all(np.isfinite(v).all() for v in fields))
    mean_mass = float(np.mean(mass))
    payload = {"num_streamlines": spool.num_streamlines, "row_count": len(spool.rows),
               "massflow_input_attribute": spool.massflow,
               "power_W": spool.total_power(), "pressure_ratio": spool.overall_pressure_ratio(),
               "eta_polytropic": spool.overall_polytropic_efficiency(),
               "finite_selected_fields": finite,
               "row_massflow_spread_relative": float(np.ptp(mass) / max(abs(mean_mass), 1e-12)),
               "history": spool.convergence_history, "rows": rows}
    return sanitize(payload)


class Instrument(ast.NodeTransformer):
    def __init__(self, n, mode):
        self.n, self.mode = n, mode

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id in ("TurbineSpool", "CompressorSpool", "Outlet"):
            if self.n is not None:
                node.keywords = [k for k in node.keywords if k.arg != "num_streamlines"]
                node.keywords.append(ast.keyword(arg="num_streamlines", value=ast.Constant(self.n)))
        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr.startswith("plot") or attr in ("export_properties", "savefig", "show", "save_convergence_history"):
                return ast.copy_location(ast.Constant(None), node)
            if attr in ("solve", "solve_balance_pressure", "solve_angle_match"):
                return ast.copy_location(ast.Call(func=ast.Name(id="_probe_solve", ctx=ast.Load()),
                    args=[node.func.value, ast.Constant(attr)], keywords=[]), node)
        return node


def execute(spec):
    import numpy as np
    from turbodesign.enums import RowType
    from turbodesign.outlet import OutletType
    from turbodesign.loss import FixedPressureLoss
    from turbodesign.loss.turbine import TD2, KackerOkapuu, AinleyMathieson, CraigCox, Traupel
    from turbodesign.loss.compressor import DiffusionLoss, AxialCompressorAungier
    factories = {"td2": TD2, "kacker_okapuu": KackerOkapuu, "ainley_mathieson": AinleyMathieson,
                 "craig_cox": CraigCox, "traupel": Traupel, "diffusion": DiffusionLoss,
                 "aungier": AxialCompressorAungier, "fixed": lambda: FixedPressureLoss(0.05)}
    captures = []

    def solve(spool, method):
        if spec.get("fixed_streamlines"):
            spool.adjust_streamlines = False
        if spec.get("warm_start"):
            getattr(spool, method)()
        override = spec.get("loss")
        if override:
            for row in spool.rows:
                row.loss_function = factories[override]()
        if spec.get("cooling"):
            from turbodesign import Coolant
            spool.rows[0].coolant = Coolant(T0=350.0, P0=600000.0, massflow_percentage=0.01, Cp=1005.0)
        if spec.get("counterrotation"):
            rotors = [r for r in spool.rows if r.row_type == RowType.Rotor]
            rotors[-1].rpm = -abs(rotors[-1].rpm)
        if spec.get("massflow_factor"):
            spool.massflow *= spec["massflow_factor"]
        if spec.get("mode") == "angle":
            spool.outlet.outlet_type = OutletType.massflow_static_pressure
            spool.outlet.total_massflow = spool.massflow
            method = "solve"
        geometry_before = [sanitize({"metal_exit_angle": r.metal_exit_angle, "axial_chord": r.axial_chord, "rpm": r.rpm}) for r in spool.rows]
        start = time.perf_counter()
        try:
            getattr(spool, method)()
        except Exception as exc:
            try:
                exc.probe_partial = snapshot(spool)
            except Exception:
                pass
            raise
        summary = snapshot(spool)
        summary["solve_seconds"] = time.perf_counter() - start
        summary["geometry_before"] = geometry_before
        summary["geometry_after"] = [sanitize({"metal_exit_angle": r.metal_exit_angle, "axial_chord": r.axial_chord, "rpm": r.rpm}) for r in spool.rows]
        if spec.get("repeat_same_object"):
            try:
                getattr(spool, method)()
            except Exception as exc:
                exc.probe_partial = summary
                raise
            again = snapshot(spool)
            summary["repeat_same_object"] = {"power_W": again["power_W"], "pressure_ratio": again["pressure_ratio"],
                                             "identical_physics": all(summary[k] == v for k, v in again.items())}
        captures.append(summary)

    script = UPSTREAM / "examples" / EXAMPLES[spec["example"]]
    tree = Instrument(spec.get("n"), spec.get("mode")).visit(ast.parse(script.read_text(encoding="utf-8-sig")))
    ast.fix_missing_locations(tree)
    namespace = {"__name__": "__phase2_probe__", "__file__": str(script), "_probe_solve": solve}
    sys.path.insert(0, str(script.parent))
    try:
        exec(compile(tree, str(script), "exec"), namespace)
        if "main" in namespace:
            namespace["main"]()
    finally:
        sys.path.remove(str(script.parent))
    if not captures:
        raise RuntimeError("Example produced no instrumented solve")
    return {"source_example": script.relative_to(UPSTREAM).as_posix(),
            "source_sha256": hashlib.sha256(script.read_bytes()).hexdigest(), "solves": captures}


def worker(spec, output):
    home = ROOT / "build/throughflow_research/isolated_home"
    # This child-only home redirects upstream's forced ~/.cache; no user setting changes.
    os.environ["USERPROFILE"] = str(home)
    os.environ["MPLBACKEND"] = "Agg"
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    manifest = json.loads((REPORTS / "backend_manifest_py312.json").read_text(encoding="utf-8"))
    for asset in manifest["loss_assets"]:
        candidate = home / ".cache/TD3_LossModels" / Path(asset["path"]).name
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != asset["sha256"]:
            raise RuntimeError("Prepared asset hash mismatch: " + candidate.name)
    network_attempts = []
    def deny_network(*args, **kwargs):
        network_attempts.append(str(args[-1]) if args else "unspecified")
        raise RuntimeError("Network disabled in phase-2 evaluation; prepare pinned assets first")
    socket.socket.connect = deny_network
    socket.create_connection = deny_network
    scratch = ROOT / "build/throughflow_research/probe_output" / spec["id"]
    scratch.mkdir(parents=True, exist_ok=True)
    os.chdir(scratch)
    script = UPSTREAM / "examples" / EXAMPLES[spec["example"]]
    result = {"case": spec, "python": sys.version, "backend_sha": PIN,
              "source_example": script.relative_to(UPSTREAM).as_posix(),
              "source_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
              "instrumentation": ["plot/export suppressed", "child-only home", "network blocked", "single BLAS thread"],
              "physical_validation": "not_certified",
              "packages": {name: metadata.version(name) for name in ("turbo-design", "numpy", "scipy", "cantera", "pyturbo-aero")}}
    started = time.perf_counter()
    capture = io.StringIO()
    with warnings.catch_warnings(record=True) as caught, contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
        warnings.simplefilter("always")
        try:
            result.update(execute(spec))
            if spec.get("aba"):
                middle = dict(spec, massflow_factor=0.8)
                execute(middle)
                again = execute(spec)
                def physics(payload):
                    return [{k: v for k, v in row.items() if k != "solve_seconds"} for row in payload["solves"]]
                result["aba_identical"] = physics(result) == physics(again)
            result["status"] = "completed"
        except Exception as exc:
            result.update(status="error", error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
            if hasattr(exc, "probe_partial"):
                result["partial_solution"] = exc.probe_partial
        result["warnings"] = sorted(set(str(w.message) for w in caught))
    result["blocked_network_attempts"] = network_attempts
    result["elapsed_seconds"] = time.perf_counter() - started
    result["written_files"] = [p.relative_to(scratch).as_posix() for p in scratch.rglob("*") if p.is_file()]
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [(n, ctypes.c_size_t) for n in (
                "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            result["peak_working_set_bytes"] = counters.PeakWorkingSetSize
    log = ROOT / "logs/throughflow_phase_0_2" / output.parent.name / (spec["id"] + ".log")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(capture.getvalue(), encoding="utf-8")
    output.write_text(json.dumps(sanitize(result), indent=2, allow_nan=False) + "\n", encoding="utf-8")


def cases():
    specs = []
    for example in ("turbine1", "turbine2", "compressor1"):
        for n in (1, 3, 5, 9, 17):
            for loss in (None, "td2" if example.startswith("turbine") else "aungier"):
                specs.append({"id": "{}_{}_{}".format(example, n, loss or "original"), "example": example, "n": n, "loss": loss})
    for loss in ("kacker_okapuu", "ainley_mathieson", "craig_cox", "traupel"):
        specs.append({"id": "turbine1_3_" + loss, "example": "turbine1", "n": 3, "loss": loss})
    specs.extend([
        {"id": "compressor1_3_diffusion", "example": "compressor1", "n": 3, "loss": "diffusion"},
        {"id": "turbine1_angle", "example": "turbine1", "n": 3, "mode": "angle"},
        {"id": "turbine1_cooling", "example": "turbine1", "n": 3, "cooling": True},
        {"id": "turbine2_counterrotation", "example": "turbine2", "n": 5, "counterrotation": True},
        {"id": "turbine1_offdesign", "example": "turbine1", "n": 3, "massflow_factor": 0.8},
        {"id": "turbine1_repeat", "example": "turbine1", "n": 3, "repeat_same_object": True},
        {"id": "compressor1_repeat", "example": "compressor1", "n": 3, "repeat_same_object": True},
        {"id": "radial_original", "example": "radial"},
        {"id": "eee_hpt_original", "example": "eee_hpt"},
        {"id": "compressor10_original", "example": "compressor10"},
    ])
    for n in (1, 3, 5, 9, 17):
        for example in ("turbine1", "turbine2"):
            specs.append({"id": "{}_{}_fixed_streamlines".format(example, n), "example": example,
                          "n": n, "fixed_streamlines": True})
    specs.extend([
        {"id": "eee_hpt_td2", "example": "eee_hpt", "loss": "td2"},
        {"id": "turbine1_angle_fixed_streamlines", "example": "turbine1", "n": 3, "mode": "angle", "fixed_streamlines": True},
        {"id": "turbine1_repeat_fixed_streamlines", "example": "turbine1", "n": 3, "repeat_same_object": True, "fixed_streamlines": True},
        {"id": "turbine1_cooling_fixed_streamlines", "example": "turbine1", "n": 3, "cooling": True, "fixed_streamlines": True},
        {"id": "turbine2_counterrotation_fixed_streamlines", "example": "turbine2", "n": 5, "counterrotation": True, "fixed_streamlines": True},
    ])
    specs.extend([
        {"id": "followup_turbine1_td2_warm", "example": "turbine1", "n": 3, "loss": "td2", "fixed_streamlines": True, "warm_start": True},
        {"id": "followup_turbine1_aba", "example": "turbine1", "n": 3, "fixed_streamlines": True, "aba": True},
        {"id": "followup_compressor10_openpyxl", "example": "compressor10"},
    ])
    for factor in (0.3, 0.5, 0.7):
        specs.append({"id": "followup_compressor_aungier_{}".format(factor), "example": "compressor1", "n": 3, "loss": "aungier", "massflow_factor": factor})
    return specs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--select", default="")
    parser.add_argument("--label", default="py312_latest")
    parser.add_argument("--timeout", type=float, default=90)
    args = parser.parse_args()
    if args.worker:
        worker(json.loads(args.worker), args.output)
        return
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=UPSTREAM, text=True).strip()
    if sha != PIN:
        raise RuntimeError("Wrong upstream SHA")
    changed = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=UPSTREAM, text=True).strip()
    if changed:
        raise RuntimeError("Upstream tracked source was modified: " + changed)
    origin = importlib.util.find_spec("turbodesign")
    if origin is None or Path(origin.origin).resolve() != (UPSTREAM / "turbodesign/__init__.py").resolve():
        raise RuntimeError("Install the pinned local upstream checkout before probing")
    outdir = REPORTS / "probes" / args.label
    outdir.mkdir(parents=True, exist_ok=True)
    for spec in cases():
        if args.select and args.select not in spec["id"]:
            continue
        output = outdir / (spec["id"] + ".json")
        command = [sys.executable, str(Path(__file__).resolve()), "--worker", json.dumps(spec), "--output", str(output)]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=args.timeout)
            if completed.returncode:
                result = {"case": spec, "status": "worker_error", "stderr": completed.stderr}
                output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        except subprocess.TimeoutExpired:
            output.write_text(json.dumps({"case": spec, "status": "timeout", "timeout_seconds": args.timeout}, indent=2) + "\n", encoding="utf-8")
        result = json.loads(output.read_text(encoding="utf-8"))
        print(spec["id"], result["status"], result.get("error", ""), flush=True)


if __name__ == "__main__":
    main()
