# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SuniMuhendis is a framework researching whether an LLM can learn to produce **valid, performant engineering designs** using physics-simulation feedback (and, later, RL). The first concrete environment is a **heat exchanger**: it takes a design (JSON), runs real engineering calculations, and returns a normalized reward in `[0.0, 1.0]`. The current weight of the codebase is the *evaluation engine* ("referee"), not model training — training (SFT/RL) is future roadmap.

## Environment & commands

- **Setup:** dependencies live in a project venv. Activate it once per shell — `source .venv/bin/activate` — then use plain `python` / `pytest` / `streamlit`. (Recreate with `python3 -m venv .venv && pip install -r requirements.txt`.)
- **Interpreter:** Python **3.9.6**. Keep all code **3.9-compatible** — no `X | Y` union syntax (use `typing.Optional`/`Union`), no `match`. PEP 585 generics (`tuple[...]`, `dict[...]`) are fine and already used.
- **Tests:** `pytest tests/ -v` — run a single file/test with `pytest tests/test_heat_exchanger_reward.py -v` or `-k <substring>`.
- **Secrets:** `HF_TOKEN` is read from `.env` (gitignored; see `.env.example`) via `python-dotenv`.

### Run targets (all from repo root, venv activated)
- `python scripts/run_heat_exchanger.py` — simulate the sample design end-to-end (demo).
- `python scripts/run_simulation.py` — core pipeline demo that exercises every failure path (schema/DRC/sim/crash) with dummy components.
- `python scripts/run_baseline.py` — generate ~10k designs via samplers, simulate all, and write the SFT dataset `datasets/sft/heat_exchanger_initial.jsonl` (designs with reward > threshold).
- `python scripts/run_hf_benchmark.py --prompt <slug> [--model NAME | --models a,b] [--repeats N]` — **automated** benchmark: send one prompt (`results/<slug>/prompt.txt`, scored by `results/<slug>/task.json`) to HF Inference Providers models listed in `configs/benchmarks/models.json`, run each through schema→DRC→sim→reward, and write one JSON per run to `results/<slug>/benchmark/<model>/`. Core loop `run_benchmark(...)` takes an injectable `client_factory` (offline-testable with `DummyRandomClient`).
- `python scripts/run_llm_eval.py --client [dummy|interactive]` — **manual** single-model chain; on success interactively prompts stdin for a model name and appends to `reports/benchmark_results.json`. Kept for cloud models tested by hand.
- `streamlit run scripts/dashboard.py` — dashboard with two sources: "HF Benchmark (results/)" averages all runs per (prompt, model); "Manuel (reports/)" shows `reports/benchmark_results.json`.

### Benchmark results layout
`results/<prompt-slug>/` holds `prompt.txt` + `task.json` (both committed); generated runs go in `results/<prompt-slug>/benchmark/<model-name>/<timestamp>.json` (gitignored via `results/**/benchmark/`). A prompt unit is self-contained: `prompt.txt` is sent verbatim; `task.json` (reward weights + targets) drives scoring.

## Architecture (the parts that need multiple files to understand)

### The 4-stage evaluation pipeline (the core contract)
Everything funnels through `BaseEnvironment.evaluate()` in `src/core/base_environment.py`:

```
design (raw dict) → [1] schema validation → [2] DRC → [3] simulate → [4] reward
```

- Stages run **cheapest-first, fail-fast**: any failure short-circuits with `reward = 0.0` and a `status` of `schema_error` / `drc_error` / `simulation_error`, plus an `error_message`. This per-stage status is the training signal for later RL.
- The **raw design dict flows through all stages** (not the validated Pydantic model). So `validate_schema`, `run_drc`, and `simulator.simulate` each receive the original dict — extra fields beyond the schema are preserved and used downstream.
- `EvaluationResult` and `RewardResult` (Pydantic, `src/core/types.py`) are the shared "language" returned everywhere.

### Layered, ABC-based, environment-agnostic core
`src/core/` defines contracts; each environment fills them. To add an environment, implement the same five pieces a heat exchanger has under `src/environments/heat_exchanger/`: `schema.py` (Pydantic), `drc.py`, `simulator.py`, `reward.py`, `env.py` (wires simulator + reward via dependency injection into `BaseEnvironment`). Nothing in `src/core/` is heat-exchanger-specific. `SimpleCache` (`src/core/cache.py`) exists but is **not** wired into `evaluate()` yet.

### Heat exchanger specifics
- **Schema is a minimal 7-field contract** (`geometry_type`, `length`, `inner_tube_di/do`, `outer_shell_di`, `number_of_tubes`, `baffle_spacing`). The **V2 simulator accepts many more optional params** via `dict.get(...)` defaults — `tube_passes`, `pitch_type`, `material`, `pitch_ratio`, `baffle_cut`, fouling resistances, nozzle sizes, and fluid operating conditions (`m_dot_hot/cold`, `T_hot_in/cold_in`, …). Fluid thermophysical properties are otherwise **hardcoded** (water), which keeps evaluation deterministic.
- **Simulator (`simulator.py`) library boundary:** tube/annulus side uses `ht` (Nusselt, ε-NTU) and `fluids` (friction factor); **shell side is hand-coded Kern/Bell-Delaware** because no library covers cross-flow over tube bundles. It also computes a cost model and mechanical/TEMA limit checks that produce `num_warnings`. Any metric coming out `NaN`/`Inf` is treated as a simulation failure.
- **Reward (`reward.py`) is multi-objective** with weights pulled from the task config: `w_heat`, `w_cost`, `w_eff`, `w_drop_tube`, `w_drop_shell` (defaults 0.4/0.3/0.2/0.05/0.05). Score is the weighted sum of component sub-rewards, normalized by total weight, then multiplied by a **warnings penalty (−10% per warning)**. It reads metrics with **V1↔V2 name fallbacks** (e.g. `heat_duty_W` else `heat_duty`), so both simulator generations work.
- **Two different pressure-drop thresholds exist on purpose:** the simulator's `MAX_DP_TUBE/SHELL` (10 kPa) only drive *warnings*; the reward's `max_dp_tube/shell` from the task config (50 kPa in `task_001.json`) drive the *score*. Don't conflate them.

### Determinism is a hard requirement
Tests assert identical output for identical input (`test_heat_exchanger_smoke.py`) because the reward must be a stable signal for future RL. Preserve determinism when touching the simulator (hence hardcoded fluid props, no randomness in the eval path).

### Model clients
`src/model_clients/`, all implementing `BaseModelClient.generate_design(prompt) -> str`:
- `HFInferenceClient` (`hf_client.py`) — **real** API client; calls Hugging Face Inference Providers (OpenAI-compatible router at `router.huggingface.co/v1`) using `HF_TOKEN`. Used by `run_hf_benchmark.py`; exposes `last_latency_ms` / `last_prompt_tokens` / `last_completion_tokens` after each call.
- `DummyRandomClient` / `HeuristicClient` — ignore the prompt, return a sampled design (offline/pipeline testing; also the injected client in `test_hf_benchmark.py`).
- `InteractiveBrowserClient` — prints the prompt and reads a pasted response from stdin (manual cloud-model testing via `run_llm_eval.py`).

### LLM output parsing
`src/parsing/json_parser.py` → `parse_llm_json()` uses the `json-repair` library to recover messy/markdown-wrapped/broken JSON (see `ARCHITECTURE_DECISIONS.md` ADR-01; constrained decoding via outlines/vLLM/guidance is a possible future move).

### Import convention
Scripts insert the repo root into `sys.path` then import `from src...`. Inside packages, relative imports are used (e.g. `from ...core.base_reward import BaseRewardFunction`). There are **no `__init__.py` files** — the project relies on implicit namespace packages.
