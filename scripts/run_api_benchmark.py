import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# .env varsa otomatik yukle (HF_TOKEN). python-dotenv yoksa sessizce gec.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from src.core.logging import setup_logger
from src.environments.heat_exchanger.env import HeatExchangerEnv
from src.environments.heat_exchanger.score import HeatExchangerScore
from src.environments.heat_exchanger.simulator import HeatExchangerSimulator
from src.model_clients.base import BaseModelClient
from src.parsing.json_parser import parse_llm_json

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_WEIGHT_KEYS = ("w_heat", "w_cost", "w_drop_tube", "w_drop_shell", "w_eff")

# Bir model_spec'ten istemci ureten fabrika tipi (test icin enjekte edilebilir).
ClientFactory = Callable[[Dict[str, Any]], BaseModelClient]


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _safe_name(name: str) -> str:
    """Model adini dosya sistemi icin guvenli klasor adina cevirir."""
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
    """Varsayilan fabrika: HF veya OpenCode istemcisi ureten fonksiyon."""
    provider = spec.get("provider", "hf")
    
    if provider == "opencode":
        from src.model_clients.opencode_client import OpenCodeClient
        return OpenCodeClient(
            model=spec["model"],
            name=spec.get("name"),
            params=spec.get("params"),
        )
    elif provider == "openrouter":
        from src.model_clients.openrouter_client import OpenRouterClient
        return OpenRouterClient(
            model=spec["model"],
            name=spec.get("name"),
            params=spec.get("params"),
        )
    else:
        from src.model_clients.hf_client import HFInferenceClient
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
    Tek bir prompt'u verilen modellere `repeats` kez gonderir, her run'i ayri JSON'a yazar.

    Klasor: <results_root>/<prompt_slug>/{prompt.txt, task.json, benchmark/<model>/<ts>-<id>.json}
    Donus: yazilan run JSON dosyalarinin yollari.
    """
    logger = logger or setup_logger("hf_benchmark")
    results_root = results_root or os.path.join(_REPO_ROOT, "results")
    prompt_dir = os.path.join(results_root, prompt_slug)

    prompt_path = os.path.join(prompt_dir, "prompt.txt")
    task_path = os.path.join(prompt_dir, "task.json")
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"prompt.txt bulunamadi: {prompt_path}")
    if not os.path.exists(task_path):
        raise FileNotFoundError(f"task.json bulunamadi: {task_path}")

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

        # Istemciyi model basina BIR KEZ kur.
        client = None
        client_err: Optional[str] = None
        try:
            client = client_factory(model)
        except Exception as e:  # noqa: BLE001
            client_err = f"{type(e).__name__}: {e}"
            logger.error(f"[{model_name}] istemci kurulamadi: {client_err}")

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
                except Exception as e:  # noqa: BLE001 - hicbir run tum kosuyu dusurmesin
                    record["status"] = "client_error"
                    record["error"] = f"{type(e).__name__}: {e}"

            with open(fpath, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written.append(fpath)
            logger.info(
                f"{progress} {model_name} | r{r} -> {record['status']} "
                f"score={record['total_reward']:.3f}"
            )

    logger.info(f"Bitti. {len(written)} run yazildi -> {os.path.join(prompt_dir, 'api_runs')}")
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
        raise SystemExit(f"models.json'da belirtilen kriterlere uyan model bulunamadi: {sorted(missing)}")
    return chosen


def main():
    parser = argparse.ArgumentParser(
        description="LLM API'leri ile prompt x model otomatik benchmark."
    )
    parser.add_argument("--prompt", required=True,
                        help="results/<slug> klasor adi (prompt.txt + task.json icerir).")
    parser.add_argument("--models", type=str, default=None,
                        help="Virgulle ayrilmis model 'name' listesi (varsayilan: hepsi).")
    parser.add_argument("--model", type=str, default=None,
                        help="Tek bir model 'name' (--models'in kisayolu).")
    parser.add_argument("--provider", type=str, default=None,
                        help="Modelleri filtrelemek icin provider adi (hf, opencode, openrouter).")
    parser.add_argument("--repeats", type=int, default=1,
                        help="Model basina bu cagrida kac run.")
    parser.add_argument("--models-config", type=str,
                        default=os.path.join(_REPO_ROOT, "configs", "benchmarks", "models.json"),
                        help="Model listesi JSON yolu.")
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
        raise SystemExit(f"models.json'da model yok veya okunamadi: {args.models_config}")

    selection = None
    if args.model:
        selection = [args.model]
    elif args.models:
        selection = [s for s in args.models.split(",") if s.strip()]
    model_specs = _select_models(all_models, selection, args.provider)

    run_benchmark(
        prompt_slug=args.prompt,
        model_specs=model_specs,
        client_factory=multi_client_factory,
        repeats=args.repeats,
        logger=logger,
    )


if __name__ == "__main__":
    main()
