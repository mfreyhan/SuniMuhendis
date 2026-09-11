import json
from pathlib import Path

import pytest

from sunimuhendis import make_env


def test_hard_task_reference_is_reproducibly_feasible():
    root = Path(__file__).resolve().parents[1]
    task = json.loads((root / "results/heat_exchanger_hard_v1/task.json").read_text())
    report = json.loads((root / "reports/hard_task_calibration.json").read_text())
    reference = report["reference"]
    env = make_env("heat_exchanger")
    result = env.evaluate(task["task_id"], task, "reference", reference["design"])
    assert result.status == "success"
    assert result.metrics["heat_duty_W"] >= task["target_heat_duty"]
    assert result.metrics["dp_tube_Pa"] <= task["max_dp_tube"]
    assert result.metrics["dp_shell_Pa"] <= task["max_dp_shell"]
    assert result.score.normalized_total == pytest.approx(reference["score"])


def test_hard_v2_top_calibration_design_is_feasible_and_reproducible():
    root = Path(__file__).resolve().parents[1]
    task = json.loads(
        (root / "results/heat_exchanger_hard_v2/task.json").read_text()
    )
    report = json.loads(
        (root / "reports/hard_task_v2_calibration.json").read_text()
    )
    reference = report["reference"]
    highest = report["highest_score"]

    assert report["simulator_version"] == "v3"
    assert report["score_version"] == "heat_exchanger_score_v3"
    assert reference["meets_targets"] is True
    assert highest["meets_targets"] is True

    env = make_env("heat_exchanger")
    result = env.evaluate(task["task_id"], task, "reference-v3", reference["design"])

    assert result.status == "success"
    assert result.metrics["heat_duty_W"] >= task["target_heat_duty"]
    assert result.metrics["dp_tube_Pa"] <= task["max_dp_tube"]
    assert result.metrics["dp_shell_Pa"] <= task["max_dp_shell"]
    assert result.score.components["num_unmet_requirements"] == 0.0
    assert result.score.normalized_total == pytest.approx(reference["score"])
