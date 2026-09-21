"""Capture the pre-throughflow referee contract without changing library code."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Research scripts must run against this checkout, not an editable install elsewhere.
sys.path.insert(0, str(ROOT / "src"))


def capture():
    from sunimuhendis import make_env
    import sunimuhendis
    task = json.loads((ROOT / "configs/tasks/heat_exchanger/task_001.json").read_text())
    design = json.loads((ROOT / "examples/designs/heat_exchanger_valid_001.json").read_text())
    multi = json.loads((ROOT / "results/zero_shot/heat_exchanger_hard_v4/task.json").read_text())
    cases = [
        ("valid", task, design, "success"),
        ("schema_error", task, dict(design, unexpected_field=1), "schema_error"),
        ("drc_error", task, dict(design, inner_tube_di=0.03), "drc_error"),
        ("multipoint", multi, multi["reference_designs"][0], "success"),
    ]
    outputs = []
    for name, params, geometry, expected in cases:
        env = make_env("heat_exchanger")
        first = env.evaluate(name, params, name, geometry).model_dump()
        second = env.evaluate(name, params, name, geometry).model_dump()
        assert first == second, name
        assert first["status"] == expected, (name, first["status"])
        outputs.append({"case": name, "task": params, "design": geometry, "result": first})
    # Deliberately injected failure pins the core error contract, not a physical claim.
    env = make_env("heat_exchanger")
    class FailedSimulator:
        def simulate(self, params):
            return False, {}, {"probe": "injected_failure"}, "phase0 deliberate failure"
    env.simulator = FailedSimulator()
    failed = env.evaluate("simulation_error", task, "injected", design).model_dump()
    assert failed["status"] == "simulation_error"
    outputs.append({"case": "simulation_error_injected", "task": task, "design": design, "result": failed})
    return outputs, str(Path(sunimuhendis.__file__).resolve())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reports/throughflow_phase_0_2/heat_exchanger_baseline.json")
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    cases, module = capture()
    if args.check:
        previous = json.loads(args.check.read_text(encoding="utf-8"))
        assert previous["cases"] == cases, "Baseline changed; inspect instead of overwriting."
        print("All five baseline cases reproduce exactly.")
        return
    payload = {
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "python": sys.version,
        "platform": platform.platform(),
        "import_path": module,
        "packages": {name: metadata.version(name) for name in ("pydantic", "ht", "fluids", "numpy", "scipy", "pytest")},
        "source_hashes": {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted((ROOT / "src/sunimuhendis").rglob("*.py"))},
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print("Captured five deterministic contract cases at", args.output)


if __name__ == "__main__":
    main()
