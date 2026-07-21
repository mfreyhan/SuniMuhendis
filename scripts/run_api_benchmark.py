import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Auto-load .env if exists (HF_TOKEN). Pass silently if python-dotenv is missing.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from sunimuhendis.core.logging import setup_logger
from sunimuhendis.environments.heat_exchanger.env import HeatExchangerEnv
from sunimuhendis.environments.heat_exchanger.score import HeatExchangerScore
from sunimuhendis.environments.heat_exchanger.simulator import HeatExchangerSimulator
from sunimuhendis.model_clients.base import BaseModelClient
from sunimuhendis.parsing.json_parser import parse_llm_json

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_WEIGHT_KEYS = ("w_heat", "w_cost", "w_drop_tube", "w_drop_shell", "w_eff")

# Factory type generating a client from model_spec (injectable for testing).
ClientFactory = Callable[[Dict[str, Any]], BaseModelClient]


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _safe_name(name: str) -> str:
    """Converts model name to a safe folder name for the file system."""
    cleaned = name.strip().replace(os.sep, "_")
    if os.altsep:
        cleaned = cleaned.replace(os.altsep, "_")
    return cleaned or "unknown"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _file_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")


def _build_environment():
    return HeatExchangerEnv(HeatExchangerSimulator(), HeatExchangerScore())


def multi_client_factory(spec: Dict[str, Any]) -> BaseModelClient:
    """Default factory: function generating HF or OpenCode client."""
    provider = spec.get("provider", "hf")
    
    if provider == "opencode":
        from sunimuhendis.model_clients.opencode_client import OpenCodeClient
        return OpenCodeClient(
            model=spec["model"],
            name=spec.get("name"),
            params=spec.get("params"),
        )
    elif provider == "openrouter":
        from sunimuhendis.model_clients.openrouter_client import OpenRouterClient
        return OpenRouterClient(
            model=spec["model"],
            name=spec.get("name"),
            params=spec.get("params"),
        )
    else:
        from sunimuhendis.model_clients.hf_client import HFInferenceClient
        return HFInferenceClient(
            model=spec["model"],
            name=spec.get("name"),
            params=spec.get("params"),
        )


def run_benchmark(
    prompt_slug: str,
    model_specs: List[Dict[str, Any]],
    client_factory: ClientFactory,
    repeats: int = 1,
    results_root: Optional[str] = None,
    logger=None,
) -> List[str]:
    """
    Sends a single prompt to given models 'repeats' times, writes each run to a separate JSON.

    Folder: <results_root>/<prompt_slug>/{prompt.txt, task.json, benchmark/<model>/<ts>-<id>.json}
    Returns: paths of the written run JSON files.
    """
    logger = logger or setup_logger("hf_benchmark")
    results_root = results_root or os.path.join(_REPO_ROOT, "results")
    prompt_dir = os.path.join(results_root, prompt_slug)

    prompt_path = os.path.join(prompt_dir, "prompt.txt")
    task_path = os.path.join(prompt_dir, "task.json")
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"prompt.txt not found: {prompt_path}")
    if not os.path.exists(task_path):
        raise FileNotFoundError(f"task.json not found: {task_path}")

    with open(prompt_path, "r", encoding="utf-8-sig") as f:
        prompt_text = f.read()
    task_params = _load_json(task_path)
    task_id = task_params.get("task_id", prompt_slug)
    weights = {k: task_params[k] for k in _WEIGHT_KEYS if k in task_params}

    env = _build_environment()
    total = len(model_specs) * repeats
    logger.info(f"Prompt '{prompt_slug}': {len(model_specs)} model x {repeats} repeat = {total} run.")

    written: List[str] = []
    done = 0
    out_dir = os.path.join(prompt_dir, "api_runs")
    os.makedirs(out_dir, exist_ok=True)
    for model in model_specs:
        model_name = model.get("name") or model.get("model")
        model_id = model.get("model", model_name)
        
        fpath = os.path.join(out_dir, f"{_safe_name(model_name)}.jsonl")

        # Instantiate client ONCE per model.
        client = None
        client_err: Optional[str] = None
        try:
            client = client_factory(model)
        except Exception as e:  # noqa: BLE001
            client_err = f"{type(e).__name__}: {e}"
            logger.error(f"[{model_name}] client could not be instantiated: {client_err}")

        for r in range(repeats):
            done += 1
            progress = f"[{done}/{total}]"
            record: Dict[str, Any] = {
                "model_name": model_name,
                "model_id": model_id,
                "prompt_slug": prompt_slug,
                "task_id": task_id,
                "timestamp": _utcnow_iso(),
                "status": "client_error",
                "weights": weights,
                "total_reward": 0.0,
                "reward_components": {},
                "metrics": {},
                "design": None,
                "raw_response": None,
                "latency_ms": 0.0,
                "prompt_tokens": None,
                "completion_tokens": None,
                "error": client_err,
            }

            if client is not None:
                try:
                    raw = client.generate_design(prompt_text)
                    record["raw_response"] = raw
                    record["latency_ms"] = getattr(client, "last_latency_ms", 0.0)
                    record["prompt_tokens"] = getattr(client, "last_prompt_tokens", None)
                    record["completion_tokens"] = getattr(client, "last_completion_tokens", None)

                    design = None
                    try:
                        design = parse_llm_json(raw)
                        record["design"] = design
                    except Exception as e:  # noqa: BLE001
                        record["status"] = "parse_error"
                        record["error"] = f"{type(e).__name__}: {e}"

                    if design is not None:
                        design_id = f"{model_name}_{r}_{uuid.uuid4().hex[:6]}"
                        result = env.evaluate(task_id, task_params, design_id, design)
                        record["status"] = result.status
                        record["total_reward"] = float(result.score.normalized_total)
                        record["reward_components"] = dict(result.score.components)
                        record["metrics"] = dict(result.metrics)
                        record["error"] = result.error_message
                except Exception as e:  # noqa: BLE001 - do not let any run crash the whole execution
                    record["status"] = "client_error"
                    record["error"] = f"{type(e).__name__}: {e}"

            with open(fpath, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written.append(fpath)
            logger.info(
                f"{progress} {model_name} | r{r} -> {record['status']} "
                f"score={record['total_reward']:.3f}"
            )

    logger.info(f"Done. {len(written)} runs written -> {os.path.join(prompt_dir, 'api_runs')}")
    return written


def _select_models(all_models: List[dict], selection: Optional[List[str]], provider: Optional[str] = None) -> List[dict]:
    if provider:
        all_models = [m for m in all_models if m.get("provider", "hf") == provider]

    if not selection:
        return all_models
    wanted = {s.strip() for s in selection}
    chosen = [m for m in all_models if (m.get("name") or m.get("model")) in wanted]
    missing = wanted - {(m.get("name") or m.get("model")) for m in chosen}
    if missing:
        raise SystemExit(f"No model matching the criteria in models.json was found: {sorted(missing)}")
    return chosen


def main():
    parser = argparse.ArgumentParser(
        description="Automated benchmark for prompt x model using LLM APIs."
    )
    parser.add_argument("--prompt", required=True,
                        help="results/<slug> folder name (contains prompt.txt + task.json).")
    parser.add_argument("--models", type=str, default=None,
                        help="Comma-separated model 'name' list (default: all).")
    parser.add_argument("--model", type=str, default=None,
                        help="A single model 'name' (shortcut for --models).")
    parser.add_argument("--provider", type=str, default=None,
                        help="Provider name to filter models (hf, opencode, openrouter).")
    parser.add_argument("--repeats", type=int, default=1,
                        help="How many runs per model in this execution.")
    parser.add_argument("--models-config", type=str,
                        default=os.path.join(_REPO_ROOT, "configs", "benchmarks", "models.json"),
                        help="Path to model list JSON.")
    args = parser.parse_args()

    logger = setup_logger("hf_benchmark")

    config_data = _load_json(args.models_config)
    all_models = []
    
    if "providers" in config_data:
        for prov_name, prov_models in config_data["providers"].items():
            for m in prov_models:
                m["provider"] = prov_name
                all_models.append(m)
    elif "models" in config_data:
        all_models = config_data["models"]

    if not all_models:
        raise SystemExit(f"No models in models.json or could not read: {args.models_config}")

    selection = None
    if args.model:
        selection = [args.model]
    elif args.models:
        selection = [s for s in args.models.split(",") if s.strip()]
    model_specs = _select_models(all_models, selection, args.provider)

    prompt_slugs = [p.strip() for p in args.prompt.split(",") if p.strip()]
    
    for slug in prompt_slugs:
        run_benchmark(
            prompt_slug=slug,
            model_specs=model_specs,
            client_factory=multi_client_factory,
            repeats=args.repeats,
            logger=logger,
        )


if __name__ == "__main__":
    main()
