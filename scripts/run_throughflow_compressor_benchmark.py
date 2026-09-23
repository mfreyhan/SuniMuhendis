"""Run a reproducible compressor comparison through the public environment API.

The one-stage case follows Mattingly example 9.1, which is also shipped as a
NASA turbo-design example.  The two-stage case repeats the stage only as a
multi-stage integration exercise; it is not experimental validation.
"""

import argparse
import contextlib
import io
import json
from pathlib import Path

from sunimuhendis import make_env

try:
    from scripts.run_throughflow_compressor import build_case
except ModuleNotFoundError:  # direct ``python scripts/...`` execution
    from run_throughflow_compressor import build_case


MATTINGLY_STAGE_PRESSURE_RATIO = 1.3


def _candidate_case(stages):
    design, task = build_case(stages=stages, streamtubes=10)
    for row in design["rows"]:
        if row["row_type"] not in ("rotor", "stator"):
            continue
        # The textbook example supplies the exit angles and annulus dimensions,
        # but not a complete manufacturable blade.  These explicit assumptions
        # complete the candidate-profile contract and remain part of the design.
        row["stagger_angle_deg"] = [30.0 + index for index in range(11)]
        row["trailing_edge_thickness_m"] = 0.0005
        if row["row_type"] == "rotor":
            row["tip_clearance_m"] = 0.0005
    task["physics_profile"] = "axial_compressor_candidate_v1"
    task["physics"] = {
        "default_loss_model": "diffusion",
        "default_deviation_model": "carter",
    }
    return design, task


def _run(label, design, task):
    with contextlib.redirect_stdout(io.StringIO()):
        result = make_env("turbomachinery_throughflow").evaluate(
            "compressor_benchmark", task, label, design
        )
    row_summary = []
    for row in result.raw_simulation_output.get("rows", []):
        row_summary.append(
            {
                "row_id": row["row_id"],
                "loss_model": row["loss_model"],
                "deviation_model": row["deviation_model"],
                "mean_loss_coefficient": sum(row["Yp"]) / len(row["Yp"]),
                "mean_deviation_deg": sum(row["deviation_deg"])
                / len(row["deviation_deg"]),
            }
        )
    return {
        "label": label,
        "status": result.status,
        "error": result.error_message,
        "reward_eligible": False,
        "metrics": result.metrics,
        "rows": row_summary,
        "fidelity_notes": result.raw_simulation_output.get("fidelity_notes", []),
    }


def run_comparison():
    runs = []
    for stages in (1, 2):
        regression_design, regression_task = build_case(stages=stages, streamtubes=10)
        candidate_design, candidate_task = _candidate_case(stages)
        runs.append(
            _run(
                "mattingly_{}_stage_regression".format(stages),
                regression_design,
                regression_task,
            )
        )
        runs.append(
            _run(
                "mattingly_{}_stage_candidate".format(stages),
                candidate_design,
                candidate_task,
            )
        )
    return {
        "reference": {
            "name": "Mattingly example 9.1",
            "one_stage_pressure_ratio": MATTINGLY_STAGE_PRESSURE_RATIO,
            "source": "NASA turbo-design examples/mattingly-axial-compressor/example9.1.py",
        },
        "interpretation": {
            "regression": "Adapter-equivalence check with zero fixed loss and zero deviation.",
            "candidate": "NASA preliminary diffusion loss plus corrected Carter deviation; solver demonstration only.",
            "two_stage": "Repeated-stage integration and 10-streamtube check, not a published benchmark design.",
        },
        "runs": runs,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument("--output", type=Path, help="also write the JSON result")
    args = parser.parse_args()
    report = run_comparison()
    payload = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    if args.json:
        print(payload)
        return
    print("case                              status       PR       target     eta_poly   residual")
    for run in report["runs"]:
        metrics = run["metrics"]
        print(
            "{:<33} {:<10} {:>8.4f} {:>8.4f} {:>10.4f} {:>10.2e}".format(
                run["label"],
                run["status"],
                metrics.get("pressure_ratio_total", float("nan")),
                metrics.get("target_pressure_ratio_total", float("nan")),
                metrics.get("efficiency_polytropic", float("nan")),
                metrics.get("massflow_residual", float("nan")),
            )
        )
    print("\nAll runs use 11 radial solution points (10 streamtubes).")
    print("Candidate results remain reward-ineligible pending experimental validation.")


if __name__ == "__main__":
    main()
