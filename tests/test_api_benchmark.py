import json
import os

from scripts.run_api_benchmark import _safe_name, _select_models, run_benchmark
from src.model_clients.dummy_random import DummyRandomClient

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


def test_select_models():
    all_models = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    assert _select_models(all_models, None) == all_models
    assert _select_models(all_models, ["b"]) == [{"name": "b"}]


def test_safe_name():
    assert _safe_name("Claude Opus 4.8") == "Claude Opus 4.8"
    assert _safe_name("a/b") == "a_b"
