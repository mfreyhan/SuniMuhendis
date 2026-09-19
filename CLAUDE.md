# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SuniMuhendis is a framework researching whether an LLM can learn to produce **valid, performant engineering designs** using physics-simulation feedback . The first concrete environment is a **heat exchanger**: it takes a design (JSON), runs real engineering calculations, and returns a normalized benchmark score in `[0.0, 1.0]`. The current weight of the codebase is the *evaluation engine* ("referee").

## Environment & commands

- **Setup:** dependencies live in a project venv. Activate it once per shell â€” `source .venv/bin/activate` â€” then use plain `python` / `pytest` / `streamlit`. (Recreate with `python3 -m venv .venv && pip install -r requirements.txt && pip install -e .`.) The `pip install -e .` step makes the `sunimuhendis` package importable.
- **Interpreter:** Python **3.9.6**. Keep all code **3.9-compatible** â€” no `X | Y` union syntax (use `typing.Optional`/`Union`), no `match`. PEP 585 generics (`tuple[...]`, `dict[...]`) are fine and already used.
- **Tests:** `pytest tests/ -v` â€” run a single file/test with `pytest tests/test_heat_exchanger_score.py -v` or `-k <substring>`.
- **Secrets:** `HF_TOKEN` is read from `.env` (gitignored; see `.env.example`) via `python-dotenv`.

### Run targets (all from repo root, venv activated)
- `python scripts/run_heat_exchanger.py` â€” simulate the sample design end-to-end (demo).
- `python scripts/run_simulation.py` â€” core pipeline demo that exercises every failure path (schema/DRC/sim/crash) with dummy components.
- `python scripts/run_baseline.py` â€” generate ~10k designs via samplers, simulate all, and write the SFT dataset `datasets/sft/heat_exchanger_initial.jsonl` (designs with score > threshold).
- `python scripts/run_api_benchmark.py --prompt <slug> [--model NAME | --models a,b] [--repeats N]` â€” **automated zero-shot** benchmark: send `results/zero_shot/<slug>/prompt.txt` (scored by the adjacent `task.json`) to configured models, run each response through schemaâ†’DRCâ†’simâ†’score, and append results under that task's `api_runs/`. Core loop `run_benchmark(...)` takes an injectable `client_factory` (offline-testable with `DummyRandomClient`).
- `python scripts/run_llm_eval.py --client [dummy|interactive] --prompt <slug>` â€” **manual zero-shot** single-model chain; on success prompts for a model name and appends to `results/zero_shot/<slug>/manual_runs/`.
- `python scripts/token_report.py [--by model|month|task] [--as-of YYYY-MM-DD] [--csv out.csv]` — all-time token and spend ledger over every recorded run. Each run is priced twice: at the rate frozen into the record when it ran, and at a current or dated price list, so historical spend and today-equivalent spend are both reportable.
- `streamlit run scripts/dashboard.py` â€” track-first dashboard with isolated task catalogs. It reads the evaluation pipeline as a funnel (responded → parsed → schema → DRC → simulated), scores requirement compliance against the task config (duty target, both ΔP limits), reports design diversity, and keeps run-level exploration and exports. Its Spend tab reports the all-time token ledger across every task and track, independent of the on-screen filters. The feedback-driven track is currently a prepared placeholder only.

### Token and cost accounting
Every benchmark record carries a `usage` block (prompt / completion / reasoning / cached / total tokens), a `pricing_snapshot` and a `cost_usd` with `cost_basis` — `provider_charged` when the provider reported what it billed, otherwise `price_snapshot`.

**Prices are read live, not from a local file.** `run_benchmark(...)` fetches `openrouter.ai/api/v1/models` once at the start of a run (`sunimuhendis.model_clients.pricing`), and freezes each model's rate plus the exact fetch timestamp into that run's record. Reading the rate from `configs/benchmarks/models.json` would attribute a run to whatever price was true at the last manual sync, which can be weeks stale. If the API is unreachable the runner logs it and falls back to the registry rates, stamped with their own older sync date; `--offline-prices` forces that path. Every benchmark also archives the live price list it used to `configs/benchmarks/pricing_history/openrouter-<date>.json` (committed), so the history needed to reprice old runs accumulates on its own; `scripts/sync_openrouter.py` writes the same file.

Repricing is live too: `scripts/token_report.py` and the dashboard's Spend tab read current prices from the API by default (`--prices local` or `--as-of <date>` to use the registry or an archived book). Records that predate all this still work — they are priced from their embedded `model_metadata.pricing`, and where even that is missing the cost is reported as unknown, never as zero.

### Benchmark results layout
Experiment tracks are top-level: active independent tasks live at `results/zero_shot/<prompt-slug>/`, while future iterative tasks will live separately at `results/feedback_driven/<feedback-task-slug>/`. Every task owns its `prompt.txt`, `task.json`, dashboard-rendered `notes.md`, and outputs; feedback-driven tasks must not implicitly reuse zero-shot definitions. The feedback track has no runner yet. The dashboard keeps the task catalogs separate and reads older layouts only for compatibility.

## Architecture (the parts that need multiple files to understand)

### The 4-stage evaluation pipeline (the core contract)
Everything funnels through `BaseEnvironment.evaluate()` in `src/core/base_environment.py`:

```
design (raw dict) â†’ [1] schema validation â†’ [2] DRC â†’ [3] simulate â†’ [4] benchmark score
```

- Stages run **cheapest-first, fail-fast**: any failure short-circuits with `score = 0.0` and a `status` of `schema_error` / `drc_error` / `simulation_error`, plus an `error_message`. This per-stage status is the evaluation feedback for the benchmark.
- The **raw design dict flows through all stages** (not the validated Pydantic model). So `validate_schema`, `run_drc`, and `simulator.simulate` each receive the original dict. Note this does **not** let a design smuggle extra fields through: `schema.py` sets `extra="forbid"`, so anything outside the 7-field contract is rejected at stage 1.
- `EvaluationResult` and `ScoreResult` (Pydantic, `src/core/types.py`) are the shared "language" returned everywhere.

### Layered, ABC-based, environment-agnostic core
`src/core/` defines contracts; each environment fills them. To add an environment, implement the same five pieces a heat exchanger has under `src/environments/heat_exchanger/`: `schema.py` (Pydantic), `drc.py`, `simulator.py`, `score.py`, `env.py` (wires simulator + benchmark score via dependency injection into `BaseEnvironment`). Nothing in `src/core/` is heat-exchanger-specific. `SimpleCache` (`src/core/cache.py`) exists but is **not** wired into `evaluate()` yet.

### Task feasibility audit (`BaseEnvironment.audit_task`)
A **second environment-agnostic contract**, alongside `evaluate()`. Where `evaluate()` scores one design, `audit_task(task_params)` audits the *task itself* — before any model is run against it — and returns an `AuditReport` (`core/types.py`).

It exists because a task can be calibrated into a wall: a target no design can reach, a penalty no design can avoid, or a reward budget that pays more for producing *any* valid design than for producing a good one. See `reports/simulator_v3_physics_audit.md` for the audit that motivated it — `heat_exchanger_hard_v2` has all three problems, and its observed score ceiling (0.783) is an artefact of them rather than a measurement of any model.

It is a **template method**: the algorithm lives in `BaseEnvironment` and is shared; each environment supplies the environment-specific parts as hooks, so `make_env("heat_exchanger").audit_task(...)` audits heat-exchanger physics and a future environment audits its own.

| Hook | Required | What it supplies |
|---|---|---|
| `sample_designs(n, seed)` | yes | Deterministic, deliberately *broad* coverage of the design space. A sampler biased towards good designs hides the walls the audit exists to find. |
| `get_requirements(task_params)` | yes | The task's hard requirements as `Requirement(name, metric_key, operator, limit)` — distinct from score weights, which only assign partial credit. |
| `list_design_checks()` | no | Catalogue of every check the environment can raise, so the audit can report *dead* checks (rules that, as configured, can never fire). |
| `analyse_physics(task_params)` | no | Closed-form limits sampling cannot prove. Keys prefixed `CRITICAL`/`WARNING` are promoted into `AuditReport.findings`. The heat exchanger reports its ε-NTU ceiling, the duty past which the LMTD-F warning becomes unavoidable, and the nozzle share of each ΔP budget. |

The hooks are **not** `@abstractmethod` — existing and dummy environments keep working, and `audit_task` fails with a message naming the missing hook.

**Use it when choosing task parameters.** `AuditReport.is_healthy()` is false when any CRITICAL finding survives; `summary()` prints the whole thing. `tests/test_task_audit.py` pins both directions: the walled task is flagged, a task with genuine headroom is not.

### Heat exchanger specifics
- **Schema is a minimal 7-field contract** (`geometry_type`, `length`, `inner_tube_di/do`, `outer_shell_di`, `number_of_tubes`, `baffle_spacing`). The simulator reads many more optional params via `dict.get(...)` defaults â€” but since the schema forbids extra fields, **none of them are reachable from a benchmarked design**; they only apply when calling the simulator directly. Treat them as an internal surface, not a design space â€” `tube_passes`, `pitch_type`, `material`, `pitch_ratio`, `baffle_cut`, fouling resistances, nozzle sizes, and fluid operating conditions (`m_dot_hot/cold`, `T_hot_in/cold_in`, â€¦). Fluid thermophysical properties are otherwise **hardcoded** (water), which keeps evaluation deterministic.
- **Simulator (`simulator.py`) library boundary:** tube/annulus side uses `ht` (Nusselt, Îµ-NTU) and `fluids` (friction factor); **shell side is hand-coded Kern/Bell-Delaware** because no library covers cross-flow over tube bundles. It also computes a cost model and mechanical/TEMA limit checks that produce `num_warnings`. Any metric coming out `NaN`/`Inf` is treated as a simulation failure.
- **Simulator is at `VERSION = "v4"`.** V4 corrected three defects the physics audit found, and **its numbers differ from V3 — results from the two must never be pooled** (~15% of designs get a different warning count). The corrections: unsupported span now follows the TEMA table keyed by tube OD instead of one flat 1.5 m; the ASME wall-thickness check uses UG-27's `t = P·R/(S·E − 0.6·P)` (the previous form *added* where the code subtracts, understating thickness by ~11% at 200 bar) and honours a joint efficiency; and `drc.py` now reads the design's own `tube_passes` / `pitch_ratio` / `pitch_type` rather than assuming the defaults, so DRC and the simulator can no longer disagree about the same design.
- **Correlation limits are reported, never charged to the design.** Kern's shell-side correlations are only valid for 2e3 < Re < 1e6, and its crossflow area assumes a bundle spanning the shell. When a design falls outside either, the simulator sets `shell_correlation_in_range` / `bundle_fill_fraction` and appends to `raw_data["fidelity_notes"]` — deliberately **not** to `warnings`, because the score penalises warnings and charging a design for the referee's blind spots would be scoring our own ignorance.
- **Benchmark Score (`score.py`) is multi-objective** with weights pulled from the task config: `w_heat`, `w_cost`, `w_eff`, `w_drop_tube`, `w_drop_shell` (defaults 0.4/0.3/0.2/0.05/0.05). Score is the weighted sum of component sub-scores, normalized by total weight, then multiplied by a **warnings penalty (âˆ’10% per warning)**. It reads metrics with **V1â†”V2 name fallbacks** (e.g. `heat_duty_W` else `heat_duty`), so both simulator generations work.
- **Two different pressure-drop thresholds exist on purpose:** the simulator's `MAX_DP_TUBE/SHELL` (10 kPa) only drive *warnings*; the score's `max_dp_tube/shell` from the task config (50 kPa in `task_001.json`) drive the *score*. Don't conflate them.

### Determinism is a hard requirement
Tests assert identical output for identical input (`test_heat_exchanger_smoke.py`) because the evaluation score must be stable and reproducible. Preserve determinism when touching the simulator (hence hardcoded fluid props, no randomness in the eval path).

### Model clients
`src/model_clients/`, all implementing `BaseModelClient.generate_design(prompt) -> str`:
- `HFInferenceClient` (`hf_client.py`) â€” **real** API client; calls Hugging Face Inference Providers (OpenAI-compatible router at `router.huggingface.co/v1`) using `HF_TOKEN`. Used by `run_api_benchmark.py`; exposes `last_latency_ms` / `last_prompt_tokens` / `last_completion_tokens` after each call.
- `DummyRandomClient` / `HeuristicClient` â€” ignore the prompt, return a sampled design (offline/pipeline testing; also the injected client in `test_hf_benchmark.py`).
- `InteractiveBrowserClient` â€” prints the prompt and reads a pasted response from stdin (manual cloud-model testing via `run_llm_eval.py`).

### LLM output parsing
`src/parsing/json_parser.py` â†’ `parse_llm_json()` uses the `json-repair` library to recover messy/markdown-wrapped/broken JSON (see `ARCHITECTURE_DECISIONS.md` ADR-01; constrained decoding via outlines/vLLM/guidance is a possible future move).

### Packaging & import convention
The library is an installable **src-layout package**: everything importable lives under `src/sunimuhendis/` and is exposed via `pyproject.toml`. Install it editable once (`pip install -e .`) so `import sunimuhendis` works everywhere; the root `conftest.py` also puts `src/` on `sys.path` for tests. Scripts import `from sunimuhendis...` (the old repo-root `sys.path` + `from src...` convention is gone). Inside the package, relative imports are used (e.g. `from ...core.base_score import BaseScoreFunction`), and every subpackage has an `__init__.py`.

**Consuming just the environments (e.g. from a separate training repo):** `pip install "sunimuhendis[heat_exchanger] @ git+<repo-url>@<tag>"`, then `from sunimuhendis import make_env, list_environments`. Instantiate by name â€” `make_env("heat_exchanger")` â€” via the registry in `environments/registry.py` (each factory imports its heavy sim deps **lazily**, so the per-env install extras are meaningful). The benchmark harness (`model_clients/`, `baselines/`, `prompts/`) lives in-tree for this repo's own scripts but is **excluded from the wheel** (see `[tool.setuptools.packages.find]` in `pyproject.toml`), so a consumer pulls only `core` + `environments` + `parsing`.
