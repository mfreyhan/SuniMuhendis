"""Run a streamtube-resolution study for the axial-compressor adapter."""

import argparse
import contextlib
import copy
import io
import json

from sunimuhendis import make_env

try:
    from scripts.run_throughflow_compressor import build_case
except ModuleNotFoundError:  # Direct execution places scripts/ on sys.path.
    from run_throughflow_compressor import build_case


COMPARISON_METRICS = (
    "power_W",
    "pressure_ratio_total",
    "efficiency_polytropic",
)


def relative_difference(value: float, reference: float) -> float:
    if reference == 0.0:
        return abs(value - reference)
    return abs(value - reference) / abs(reference)


def run_study(stages: int, streamtube_counts: list[int]) -> dict[str, object]:
    if not streamtube_counts or any(value < 1 for value in streamtube_counts):
        raise ValueError("streamtube counts must be positive")
    if streamtube_counts != sorted(set(streamtube_counts)):
        raise ValueError("streamtube counts must be unique and increasing")

    design, base_task = build_case(stages=stages, streamtubes=streamtube_counts[0])
    env = make_env("turbomachinery_throughflow")
    observations = []
    for streamtubes in streamtube_counts:
        task = copy.deepcopy(base_task)
        task["numerics"]["streamlines"] = streamtubes + 1
        with contextlib.redirect_stdout(io.StringIO()):
            result = env.evaluate(
                "compressor_resolution_study",
                task,
                "{}stage_{}streamtube".format(stages, streamtubes),
                design,
            )
        observations.append(
            {
                "streamtubes": streamtubes,
                "streamlines": streamtubes + 1,
                "status": result.status,
                "metrics": {
                    name: result.metrics.get(name) for name in COMPARISON_METRICS
                },
                "error_message": result.error_message,
            }
        )

    if any(item["status"] != "success" for item in observations):
        return {
            "study_type": "numerical_resolution",
            "physical_validation": False,
            "stages": stages,
            "observations": observations,
        }

    reference = observations[-1]
    for observation in observations:
        observation["relative_difference_to_finest"] = {
            name: relative_difference(
                observation["metrics"][name], reference["metrics"][name]
            )
            for name in COMPARISON_METRICS
        }

    return {
        "study_type": "numerical_resolution",
        "physical_validation": False,
        "stages": stages,
        "reference_streamtubes": reference["streamtubes"],
        "observations": observations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stages", type=int, default=2)
    parser.add_argument("--streamtubes", default="2,5,10,20")
    args = parser.parse_args()
    counts = [int(value) for value in args.streamtubes.split(",")]
    print(json.dumps(run_study(args.stages, counts), indent=2))


if __name__ == "__main__":
    main()
