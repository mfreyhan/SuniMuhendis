import argparse
import json
import os
import sys
import uuid
import glob
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from sunimuhendis.core.logging import setup_logger
from sunimuhendis.environments.heat_exchanger.env import HeatExchangerEnv
from sunimuhendis.environments.heat_exchanger.score import HeatExchangerScoreV1
from sunimuhendis.environments.heat_exchanger.simulator import HeatExchangerSimulator
from sunimuhendis.model_clients.base import BaseModelClient
from sunimuhendis.parsing.json_parser import parse_llm_json

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_WEIGHT_KEYS = ("w_heat", "w_cost", "w_drop_tube", "w_drop_shell", "w_eff")

ClientFactory = Callable[[Dict[str, Any]], BaseModelClient]

def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def _safe_name(name: str) -> str:
    cleaned = name.strip().replace(os.sep, "_")
    if os.altsep:
        cleaned = cleaned.replace(os.altsep, "_")
    return cleaned or "unknown"

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _build_environment():
    # Pass a default V1 score, it will be overridden in evaluate if task specifies it
    return HeatExchangerEnv(HeatExchangerSimulator(), HeatExchangerScoreV1())

def multi_client_factory(spec: Dict[str, Any]) -> BaseModelClient:
    provider = spec.get("provider", "hf")
    
    if provider == "opencode":
        from sunimuhendis.model_clients.opencode_client import OpenCodeClient
        return OpenCodeClient(model=spec["model"], name=spec.get("name"), params=spec.get("params"))
    elif provider == "openrouter":
        from sunimuhendis.model_clients.openrouter_client import OpenRouterClient
        return OpenRouterClient(model=spec["model"], name=spec.get("name"), params=spec.get("params"))
    else:
        from sunimuhendis.model_clients.hf_client import HFInferenceClient
        return HFInferenceClient(model=spec["model"], name=spec.get("name"), params=spec.get("params"))

def run_benchmark(
    prompt_slug: str,
    task_path: str,
    model_specs: List[Dict[str, Any]],
    client_factory: ClientFactory,
    repeats: int = 1,
    score_version_override: Optional[str] = None,
    results_root: Optional[str] = None,
    logger=None,
) -> List[str]:
    logger = logger or setup_logger("hf_benchmark")
    results_root = results_root or os.path.join(_REPO_ROOT, "results")
    prompt_dir = os.path.join(results_root, prompt_slug)
    prompt_path = os.path.join(prompt_dir, "prompt.txt")
    
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"prompt.txt not found: {prompt_path}")
    if not os.path.exists(task_path):
        raise FileNotFoundError(f"task.json not found: {task_path}")

    with open(prompt_path, "r", encoding="utf-8-sig") as f:
        prompt_text = f.read()
        
    task_params = _load_json(task_path)
    
    if score_version_override:
        task_params["score_version"] = score_version_override
        
    task_id = task_params.get("task_id", os.path.basename(task_path).replace('.json',''))
    task_set_version = task_params.get("task_set_version", "v1")
    used_score_version = task_params.get("score_version", "heat_exchanger_score_v1")
    
    weights = {k: task_params[k] for k in _WEIGHT_KEYS if k in task_params}
    env = _build_environment()
    total = len(model_specs) * repeats
    logger.info(f"Task '{task_id}' (Prompt '{prompt_slug}'): {len(model_specs)} models x {repeats} repeats = {total} runs.")

    written: List[str] = []
    done = 0
    # Save results in prompt_dir / api_runs / task_id /
    out_dir = os.path.join(prompt_dir, "api_runs", task_id)
    os.makedirs(out_dir, exist_ok=True)
    
    for model in model_specs:
        model_name = model.get("name") or model.get("model")
        model_id = model.get("model", model_name)
        fpath = os.path.join(out_dir, f"{_safe_name(model_name)}.jsonl")

        client = None
        client_err: Optional[str] = None
        try:
            client = client_factory(model)
        except Exception as e:
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
                "task_set_version": task_set_version,
                "score_version": used_score_version,
                "simulator_version": "v2", 
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
                    except Exception as e:
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
                except Exception as e:
                    record["status"] = "client_error"
                    record["error"] = f"{type(e).__name__}: {e}"

            with open(fpath, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written.append(fpath)
            logger.info(f"{progress} {model_name} | r{r} -> {record['status']} score={record['total_reward']:.3f}")

    logger.info(f"Done for task {task_id}.")
    return written

def _select_models(all_models: List[dict], selection: Optional[List[str]], provider: Optional[str] = None) -> List[dict]:
    if provider:
        all_models = [m for m in all_models if m.get("provider", "hf") == provider]

    filtered_models = all_models
    if selection:
        wanted = {s.strip() for s in selection}
        filtered_models = [m for m in all_models if (m.get("name") or m.get("model")) in wanted]
        missing = wanted - {(m.get("name") or m.get("model")) for m in filtered_models}
        if missing:
            raise SystemExit(f"No model matching the criteria in models.json was found: {sorted(missing)}")
            
    # Deduplicate by name, preferring free models
    deduped = {}
    for m in filtered_models:
        name = m.get("name") or m.get("model")
        model_id = m.get("model", "")
        if name not in deduped:
            deduped[name] = m
        else:
            existing_model_id = deduped[name].get("model", "")
            if ":free" in model_id.lower() and ":free" not in existing_model_id.lower():
                deduped[name] = m
                
    return list(deduped.values())

def main():
    parser = argparse.ArgumentParser(description="Automated benchmark for prompt x model using LLM APIs.")
    parser.add_argument("--prompt", required=True, help="results/<slug> folder name (contains prompt.txt).")
    parser.add_argument("--task", type=str, default=None, help="Path to a specific task JSON file (e.g. results/heat_exchanger_taskset_v2/task_balanced.json)")
    parser.add_argument("--task-set", type=str, default=None, help="Name of the task set folder in results/ (e.g. heat_exchanger_taskset_v2). If omitted, falls back to prompt_slug/task.json")
    parser.add_argument("--score-version", type=str, default=None, help="Override score version (e.g. heat_exchanger_score_v2)")
    parser.add_argument("--models", type=str, default=None, help="Comma-separated model 'name' list.")
    parser.add_argument("--model", type=str, default=None, help="A single model 'name' (shortcut for --models).")
    parser.add_argument("--provider", type=str, default=None, help="Provider name to filter models.")
    parser.add_argument("--repeats", type=int, default=1, help="How many runs per model in this execution.")
    parser.add_argument("--models-config", type=str, default=os.path.join(_REPO_ROOT, "configs", "benchmarks", "models.json"))
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
    if args.model: selection = [args.model]
    elif args.models: selection = [s for s in args.models.split(",") if s.strip()]
    model_specs = _select_models(all_models, selection, args.provider)

    prompt_slugs = [p.strip() for p in args.prompt.split(",") if p.strip()]
    
    for prompt_slug in prompt_slugs:
        task_paths = []
        if args.task:
            if not os.path.isfile(args.task):
                # Try relative to repo root if absolute fails
                repo_task = os.path.join(_REPO_ROOT, args.task)
                if os.path.isfile(repo_task):
                    args.task = repo_task
                else:
                    raise FileNotFoundError(f"Task file not found: {args.task}")
            task_paths = [args.task]
        elif args.task_set:
            ts_dir = os.path.join(_REPO_ROOT, "results", args.task_set)
            if not os.path.isdir(ts_dir):
                raise NotADirectoryError(f"Task set directory not found: {ts_dir}")
            task_paths = glob.glob(os.path.join(ts_dir, "*.json"))
        else:
            task_paths = [os.path.join(_REPO_ROOT, "results", prompt_slug, "task.json")]
            
        for tp in task_paths:
            run_benchmark(
                prompt_slug=prompt_slug,
                task_path=tp,
                model_specs=model_specs,
                client_factory=multi_client_factory,
                repeats=args.repeats,
                score_version_override=args.score_version,
                logger=logger,
            )

if __name__ == "__main__":
    main()
