import json

import pandas as pd

from scripts.dashboard import (
    MAX_LABEL_CHARS,
    _error_pattern,
    _model_label_map,
    aggregate_runs,
    discover_prompt_units,
    flatten_record,
    load_all_runs,
    load_task_notes,
    pipeline_funnel,
)


def test_flatten_record_preserves_details_and_estimates_cost():
    record = {
        "model_name": "model-a",
        "status": "success",
        "total_reward": 0.75,
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "latency_ms": 2500,
        "model_metadata": {
            "pricing": {"prompt": "0.001", "completion": "0.002"},
        },
        "task_params": {
            "target_heat_duty": 200000,
            "max_dp_tube": 5000,
            "max_dp_shell": 6000,
        },
        "metrics": {
            "heat_duty_W": 210000,
            "dp_tube_Pa": 2000,
            "dp_shell_Pa": 3000,
            "effectiveness": 0.6,
            "cost_annualised_USD_per_yr": 4000,
        },
        "design": {"number_of_tubes": 80},
        "raw_response": "{\"number_of_tubes\": 80}",
    }

    row = flatten_record(record, "api_runs", "prompt-a", "model-a.jsonl", 3)

    assert row["score"] == 0.75
    assert row["heat_duty_kw"] == 210.0
    assert row["dp_tube_kpa"] == 2.0
    assert row["effectiveness_pct"] == 60.0
    assert row["latency_s"] == 2.5
    assert row["total_tokens"] == 150.0
    assert row["estimated_cost_usd"] == 0.2
    assert row["experiment_track"] == "zero_shot"
    assert row["evaluation_mode"] == "zero_shot"
    assert json.loads(row["design_json"])["number_of_tubes"] == 80


def test_flatten_record_does_not_turn_missing_metrics_into_zero():
    row = flatten_record(
        {"model_name": "empty", "status": "empty_response", "total_reward": 0.0},
        "api_runs",
        "prompt-a",
    )

    assert row["score"] == 0.0
    assert row["heat_duty_kw"] is None
    assert row["annual_cost_usd"] is None
    assert row["latency_s"] is None
    assert row["has_json"] is False


def test_aggregate_runs_includes_model_failures_in_mean_score():
    records = [
        flatten_record(
            {"model_name": "model-a", "status": "success", "total_reward": 0.8},
            "api_runs",
            "prompt-a",
            line_number=1,
        ),
        flatten_record(
            {"model_name": "model-a", "status": "parse_error", "total_reward": 0.0},
            "api_runs",
            "prompt-a",
            line_number=2,
        ),
        flatten_record(
            {"model_name": "model-a", "status": "client_error", "total_reward": 0.0},
            "api_runs",
            "prompt-a",
            line_number=3,
        ),
    ]

    summary = aggregate_runs(pd.DataFrame(records)).iloc[0]

    assert summary["Runs"] == 3
    assert summary["Non-client runs"] == 2
    assert summary["Mean score"] == 0.4
    assert summary["Successful score"] == 0.8
    assert summary["Valid design %"] == 100.0 / 3.0
    assert summary["JSON %"] == 100.0 / 3.0


def test_aggregate_runs_reports_requirement_compliance_and_diversity():
    def run(status, score, tubes, heat_w, dp_pa):
        return flatten_record(
            {
                "model_name": "model-a",
                "status": status,
                "total_reward": score,
                "design": {"number_of_tubes": tubes},
                "metrics": {
                    "heat_duty_W": heat_w,
                    "dp_tube_Pa": dp_pa,
                    "dp_shell_Pa": dp_pa,
                    "num_warnings": 0,
                },
            },
            "api_runs",
            "prompt-a",
        )

    task = {"target_heat_duty": 200000, "max_dp_tube": 5000, "max_dp_shell": 5000}
    records = [
        run("success", 0.9, 80, 210000, 2000),   # meets everything
        run("success", 0.5, 80, 210000, 2000),   # identical design, meets everything
        run("success", 0.4, 60, 150000, 2000),   # misses the duty target
        run("drc_error", 0.0, 0, 0, 0),
    ]

    summary = aggregate_runs(pd.DataFrame(records), task).iloc[0]

    assert summary["Runs"] == 4
    assert summary["Valid design %"] == 75.0
    assert summary["Requirements met %"] == 50.0
    # Two of the three valid designs are byte-identical geometry.
    assert summary["Distinct designs"] == 2


def test_pipeline_funnel_counts_survivors_per_stage():
    records = [
        flatten_record({"model_name": "m", "status": status}, "api_runs", "prompt-a")
        for status in ("success", "success", "drc_error", "schema_error", "empty_response")
    ]

    funnel = pipeline_funnel(pd.DataFrame(records)).set_index("Stage")

    assert funnel.loc["Responded", "Runs"] == 4
    assert funnel.loc["Schema valid", "Runs"] == 3
    assert funnel.loc["DRC passed", "Runs"] == 2
    assert funnel.loc["Simulated", "Runs"] == 2
    assert funnel.loc["DRC passed", "Lost here"] == 1


def test_error_pattern_groups_runs_that_failed_the_same_way():
    first = _error_pattern("DRC Error: bundle diameter 0.3317 m exceeds shell 0.2508 m")
    second = _error_pattern("DRC Error: bundle diameter 0.5404 m exceeds shell 0.1968 m")

    assert first == second
    assert _error_pattern("") == "No details recorded"


def test_model_labels_stay_unique_and_keep_the_reasoning_variant():
    labels = _model_label_map([
        "qwen3.8-27b__reasoning-low",
        "qwen3.8-27b__reasoning-medium",
        "nemotron-3-nano-omni-30b-a3b-reasoning",
    ])

    assert labels["qwen3.8-27b__reasoning-low"].endswith("·low")
    assert labels["qwen3.8-27b__reasoning-medium"].endswith("·medium")
    assert len(set(labels.values())) == 3
    assert all(len(label) <= MAX_LABEL_CHARS for label in labels.values())


def test_load_all_runs_reports_broken_json_lines(tmp_path):
    run_dir = tmp_path / "zero_shot" / "prompt-a" / "api_runs"
    run_dir.mkdir(parents=True)
    path = run_dir / "model-a.jsonl"
    path.write_text(
        json.dumps({"model_name": "model-a", "status": "success"}) + "\n{broken\n",
        encoding="utf-8",
    )

    frame, errors = load_all_runs(str(tmp_path))

    assert len(frame) == 1
    assert frame.iloc[0]["prompt"] == "prompt-a"
    assert frame.iloc[0]["experiment_track"] == "zero_shot"
    assert len(errors) == 1
    assert errors[0]["Line"] == 2


def test_load_all_runs_keeps_legacy_layout_as_zero_shot(tmp_path):
    run_dir = tmp_path / "legacy-prompt" / "api_runs"
    run_dir.mkdir(parents=True)
    (run_dir / "model-a.jsonl").write_text(
        json.dumps({"model_name": "model-a", "status": "success"}) + "\n",
        encoding="utf-8",
    )

    frame, errors = load_all_runs(str(tmp_path))

    assert errors == []
    assert len(frame) == 1
    assert frame.iloc[0]["experiment_track"] == "zero_shot"


def test_load_all_runs_keeps_transitional_nested_track_layout(tmp_path):
    run_dir = tmp_path / "nested-prompt" / "zero_shot" / "api_runs"
    run_dir.mkdir(parents=True)
    (run_dir / "model-a.jsonl").write_text(
        json.dumps({"model_name": "model-a", "status": "success"}) + "\n",
        encoding="utf-8",
    )

    frame, errors = load_all_runs(str(tmp_path))

    assert errors == []
    assert len(frame) == 1
    assert frame.iloc[0]["prompt"] == "nested-prompt"
    assert frame.iloc[0]["experiment_track"] == "zero_shot"


def test_load_all_runs_discovers_reserved_feedback_track(tmp_path):
    run_dir = tmp_path / "feedback_driven" / "feedback-task-a" / "api_runs"
    run_dir.mkdir(parents=True)
    (run_dir / "model-a.jsonl").write_text(
        json.dumps({
            "evaluation_mode": "feedback_driven",
            "model_name": "model-a",
            "status": "success",
            "total_reward": 0.9,
        }) + "\n",
        encoding="utf-8",
    )

    frame, errors = load_all_runs(str(tmp_path))

    assert errors == []
    assert len(frame) == 1
    assert frame.iloc[0]["prompt"] == "feedback-task-a"
    assert frame.iloc[0]["experiment_track"] == "feedback_driven"
    assert frame.iloc[0]["evaluation_mode"] == "feedback_driven"


def test_prompt_units_are_discovered_within_their_own_track(tmp_path):
    for track, prompt in (
        ("zero_shot", "zero-task"),
        ("feedback_driven", "feedback-task"),
    ):
        unit = tmp_path / track / prompt
        unit.mkdir(parents=True)
        (unit / "prompt.txt").write_text("prompt", encoding="utf-8")
        (unit / "task.json").write_text("{}", encoding="utf-8")

    assert discover_prompt_units(str(tmp_path), "zero_shot") == ["zero-task"]
    assert discover_prompt_units(str(tmp_path), "feedback_driven") == ["feedback-task"]


def test_task_notes_are_scoped_to_the_selected_track(tmp_path):
    zero_task = tmp_path / "zero_shot" / "shared-slug"
    feedback_task = tmp_path / "feedback_driven" / "shared-slug"
    zero_task.mkdir(parents=True)
    feedback_task.mkdir(parents=True)
    (zero_task / "notes.md").write_text("Zero-shot note", encoding="utf-8")
    (feedback_task / "notes.md").write_text("Feedback note", encoding="utf-8")

    assert load_task_notes(str(tmp_path), "zero_shot", "shared-slug") == "Zero-shot note"
    assert load_task_notes(str(tmp_path), "feedback_driven", "shared-slug") == "Feedback note"
    assert load_task_notes(str(tmp_path), "zero_shot", "missing") == ""
