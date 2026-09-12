import json
import os
from pathlib import Path

import pytest

from scripts.run_api_benchmark import (
    _apply_reasoning_effort,
    _configure_reasoning,
    _preflight_model,
    _prompt_reasoning_effort,
    _reasoning_choices,
    _safe_name,
    _select_models,
    run_benchmark,
)
from sunimuhendis.model_clients.dummy_random import DummyRandomClient

_VALID_STATUS = {
    "success", "schema_error", "drc_error", "simulation_error",
    "parse_error", "client_error",
}


def _make_prompt_unit(root, slug="he_test"):
    prompt_dir = os.path.join(root, slug)
    os.makedirs(prompt_dir, exist_ok=True)
    with open(os.path.join(prompt_dir, "prompt.txt"), "w", encoding="utf-8") as f:
        f.write("Design a heat exchanger. Output ONLY valid JSON.")
    task = {
        "task_id": "he_test_001",
        "w_heat": 0.4, "w_drop_tube": 0.05, "w_drop_shell": 0.05,
        "w_eff": 0.2, "w_cost": 0.3,
        "target_heat_duty": 150000.0, "max_dp_tube": 50000.0, "max_dp_shell": 50000.0,
    }
    with open(os.path.join(prompt_dir, "task.json"), "w", encoding="utf-8") as f:
        json.dump(task, f)
    return slug


def test_run_benchmark_offline(tmp_path):
    slug = _make_prompt_unit(str(tmp_path))
    specs = [{"name": "dummy-A"}, {"name": "dummy-B"}]

    written = run_benchmark(
        prompt_slug=slug,
        model_specs=specs,
        client_factory=lambda spec: DummyRandomClient(),
        repeats=2,
        results_root=str(tmp_path),
    )

    # 2 model = 2 run dosyasi (her biri jsonl)
    assert len(set(written)) == 2
    for p in written:
        assert os.path.exists(p)
        assert p.endswith(".jsonl")

    rec = json.loads(open(written[0], encoding="utf-8").readline())
    for field in ("model_name", "prompt_slug", "task_id", "status",
                  "total_reward", "weights", "metrics", "design"):
        assert field in rec
    assert rec["status"] in _VALID_STATUS
    assert rec["prompt_slug"] == slug
    assert rec["weights"]["w_heat"] == 0.4


def test_run_benchmark_client_error_isolated(tmp_path):
    slug = _make_prompt_unit(str(tmp_path))

    def boom_factory(spec):
        raise RuntimeError("no token")

    written = run_benchmark(
        prompt_slug=slug,
        model_specs=[{"name": "broken"}],
        client_factory=boom_factory,
        repeats=1,
        results_root=str(tmp_path),
    )
    assert len(written) == 1
    rec = json.loads(open(written[0], encoding="utf-8").read())
    assert rec["status"] == "client_error"
    assert rec["error"]


def test_run_benchmark_preflight_failure_makes_no_client_calls(tmp_path):
    slug = _make_prompt_unit(str(tmp_path))
    calls = []
    spec = {
        "name": "unsafe-router",
        "metadata": {
            "context_length": 100000,
            "supported_parameters": ["temperature"],
        },
    }

    written = run_benchmark(
        prompt_slug=slug,
        model_specs=[spec],
        client_factory=lambda model: calls.append(model),
        repeats=20,
        results_root=str(tmp_path),
    )

    assert written == []
    assert calls == []


def test_select_models():
    all_models = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    assert _select_models(all_models, None) == all_models
    assert _select_models(all_models, ["b"]) == [{"name": "b"}]


def test_safe_name():
    assert _safe_name("Claude Opus 4.8") == "Claude Opus 4.8"
    assert _safe_name("a/b") == "a_b"


def test_apply_reasoning_effort_creates_distinct_run_variant():
    original = [{
        "name": "kimi-k2.6",
        "model": "moonshotai/kimi-k2.6",
        "provider": "openrouter",
        "params": {"temperature": 0.7, "max_tokens": 8192},
    }]

    configured = _apply_reasoning_effort(original, "none")

    assert configured[0]["name"] == "kimi-k2.6__reasoning-none"
    assert configured[0]["reasoning_mode"] == "none"
    extra_body = configured[0]["params"]["extra_body"]
    assert extra_body["reasoning"] == {"effort": "none"}
    assert extra_body["provider"]["require_parameters"] is True
    assert "extra_body" not in original[0]["params"]


def test_apply_reasoning_effort_omitted_keeps_model_name():
    original = [{"name": "plain", "params": {"temperature": 0.7}}]
    assert _apply_reasoning_effort(original, None) == original


def test_apply_default_reasoning_only_changes_variant_name():
    original = [{"name": "model-a", "provider": "openrouter", "params": {}}]
    configured = _apply_reasoning_effort(original, "default")
    assert configured[0]["name"] == "model-a__reasoning-default"
    assert configured[0]["reasoning_mode"] == "default"
    assert configured[0]["params"] == {}


def test_reasoning_choices_use_synced_capabilities():
    kimi = {
        "metadata": {
            "supported_parameters": ["reasoning"],
            "reasoning": {"mandatory": False, "default_enabled": True},
        }
    }
    assert _reasoning_choices(kimi) == ["default", "none"]

    model_with_levels = {
        "metadata": {
            "supported_parameters": ["reasoning", "reasoning_effort"],
            "reasoning": {
                "mandatory": False,
                "default_effort": "medium",
                "supported_efforts": ["high", "medium", "low", "none"],
            },
        }
    }
    assert _reasoning_choices(model_with_levels) == [
        "default", "high", "medium", "low", "none",
    ]


def test_prompt_reasoning_effort_uses_numbered_choice():
    spec = {
        "name": "kimi-k2.6",
        "metadata": {
            "supported_parameters": ["reasoning"],
            "reasoning": {"mandatory": False, "default_enabled": True},
        },
    }
    output = []
    selected = _prompt_reasoning_effort(
        spec,
        input_func=lambda prompt: "2",
        print_func=output.append,
    )
    assert selected == "none"
    assert any("Reasoning mode for kimi-k2.6" in line for line in output)


def test_configure_reasoning_rejects_unadvertised_effort():
    spec = {
        "name": "kimi-k2.6",
        "metadata": {
            "supported_parameters": ["reasoning"],
            "reasoning": {"mandatory": False, "default_enabled": True},
        },
    }
    with pytest.raises(SystemExit, match="not advertised"):
        _configure_reasoning([spec], requested_effort="low", interactive=False)


def test_preflight_clamps_limits_and_omits_unsupported_temperature():
    spec = {
        "name": "small-output-model",
        "params": {"temperature": 0.1, "max_tokens": 99999},
        "metadata": {
            "context_length": 131072,
            "max_completion_tokens": 4096,
            "supported_parameters": ["max_tokens"],
        },
    }

    configured, report = _preflight_model(
        spec,
        "short prompt",
        max_output_tokens=8192,
        temperature=0.7,
    )

    assert report["status"] == "ready"
    assert report["effective_params"] == {"max_tokens": 4096}
    assert configured["params"] == {"max_tokens": 4096}
    assert any("model maximum 4096" in item for item in report["adjustments"])
    assert any("temperature omitted" in item for item in report["adjustments"])


def test_preflight_rejects_model_without_token_limit_support():
    spec = {
        "name": "unbounded-router",
        "metadata": {
            "context_length": 1000000,
            "max_completion_tokens": None,
            "supported_parameters": ["temperature"],
        },
    }
    _, report = _preflight_model(spec, "prompt")
    assert report["status"] == "error"
    assert any("fixed-budget run is unsafe" in item for item in report["errors"])


def test_preflight_uses_max_completion_tokens_when_required():
    spec = {
        "name": "completion-limit-model",
        "metadata": {
            "context_length": 100000,
            "max_completion_tokens": 12000,
            "supported_parameters": ["max_completion_tokens", "temperature"],
        },
    }
    configured, report = _preflight_model(spec, "prompt")
    assert report["status"] == "ready"
    assert configured["params"]["max_completion_tokens"] == 8192
    assert "max_tokens" not in configured["params"]


def test_preflight_clamps_to_context_budget():
    spec = {
        "name": "tiny-context",
        "metadata": {
            "context_length": 1000,
            "max_completion_tokens": 900,
            "supported_parameters": ["max_tokens", "temperature"],
        },
    }
    _, report = _preflight_model(spec, "x" * 1200, max_output_tokens=900)
    assert report["status"] == "ready"
    assert report["effective_params"]["max_tokens"] == 344


@pytest.mark.parametrize(
    ("slug", "score_version"),
    [
        ("heat_exchanger_v1", "heat_exchanger_score_v1"),
        ("heat_exchanger_v2", "heat_exchanger_score_v1"),
        ("heat_exchanger_v3", "heat_exchanger_score_v1"),
        ("heat_exchanger_v4", "heat_exchanger_score_v1"),
        ("heat_exchanger_hard_v1", "heat_exchanger_score_v1"),
        ("heat_exchanger_hard_v2", "heat_exchanger_score_v3"),
    ],
)
def test_active_prompt_targets_match_task(slug, score_version):
    root = Path(__file__).resolve().parents[1]
    unit = root / "results" / slug
    prompt = (unit / "prompt.txt").read_text(encoding="utf-8-sig")
    task = json.loads((unit / "task.json").read_text(encoding="utf-8-sig"))
    details = prompt.split("Task Details:", 1)[1].lstrip()
    stated, _ = json.JSONDecoder().raw_decode(details)
    for key, value in stated.items():
        assert task[key] == value
    assert task.get("score_version", "heat_exchanger_score_v1") == score_version


def test_benchmark_sends_and_records_paired_prompt(tmp_path):
    slug = _make_prompt_unit(str(tmp_path))
    expected = (tmp_path / slug / "prompt.txt").read_text()
    received = []

    class CapturingClient:
        def generate_design(self, prompt):
            received.append(prompt)
            return "{}"

    paths = run_benchmark(
        prompt_slug=slug, model_specs=[{"name": "capture"}],
        client_factory=lambda spec: CapturingClient(), results_root=str(tmp_path),
    )
    assert received == [expected]
    assert Path(paths[0]).parent == tmp_path / slug / "api_runs"
    record = json.loads(Path(paths[0]).read_text())
    assert record["prompt_text"] == expected
    assert record["task_params"]["target_heat_duty"] == 150000.0
    assert record["score_version"] == "heat_exchanger_score_v1"
    assert record["requested_params"] == {"max_tokens": 8192, "temperature": 0.7}
    assert record["inference_params"] == {"max_tokens": 8192, "temperature": 0.7}
    assert record["effective_params"] == {"max_tokens": 8192, "temperature": 0.7}
    assert record["parameter_adjustments"] == []
    assert record["model_metadata"] == {}
    assert record["reasoning_mode"] is None
