# SuniMuhendis

**A physics-grounded evaluation framework for machine-generated engineering designs.**

SuniMuhendis investigates whether language models can learn to produce engineering designs that are not merely well-formed, but *valid and performant* — judged by real engineering calculation rather than by human preference or textual similarity.

The premise is that design is one of the few domains where a machine's output can be graded objectively and at scale. A proposed heat exchanger either transfers the required heat within its pressure budget or it does not, and a simulator can say which, deterministically, in milliseconds. That makes design feedback cheap enough to benchmark against — and, in principle, to learn from.

The centre of gravity of this repository is therefore the **referee**: the evaluation engine that turns a design into a number you can trust.

---

## What is in this repository

| | |
|---|---|
| **Evaluation environments** | The referee — schema, design rule checks, physics simulator, and benchmark score for each engineering domain. Distributed as an installable library. |
| **Benchmark harness** | Sends tasks to commercial and open models, runs every response through the identical pipeline, and records the result with full provenance and cost. Lives in-tree; not part of the shipped library. |
| **Results and analysis** | Benchmark records, a Streamlit dashboard, a token and spend ledger, and engineering audits of the referee itself. |

### What is not in this repository

We train our own models against these environments. **That work lives in a separate, private repository, and its methodology is not published here.** This repository deliberately contains only the evaluation side: the environments, the benchmark harness, and the results of evaluating third-party models.

The separation is intentional and practical. The referee has to be credible independently of any model trained against it, so it is developed, audited, and versioned on its own terms. It is also the part that is useful to other people regardless of what we do with it.

---

## How evaluation works

Every design funnels through four stages, cheapest first, failing fast:

```
design (JSON)  →  [1] schema  →  [2] design rule check  →  [3] simulate  →  [4] score
```

| Stage | Rejects | On failure |
|---|---|---|
| **1. Schema** | Wrong types, missing or extra fields | `schema_error`, score `0.0` |
| **2. Design rule check** | Geometrically impossible designs (bundle larger than its shell, inner diameter exceeding outer) | `drc_error`, score `0.0` |
| **3. Simulation** | Designs that cannot be computed, or produce `NaN`/`Inf` | `simulation_error`, score `0.0` |
| **4. Score** | — | Normalised score in `[0.0, 1.0]` |

The per-stage status is the point, not a by-product: it says *where* a model failed, which is the feedback signal the research question depends on.

### Two properties the referee is held to

**Determinism.** Identical input produces byte-identical output. Fluid properties are fixed and no randomness enters the evaluation path. A score that drifts is not a measurement.

**Explicit versioning.** Simulators and score functions are versioned, and every stored result records which versions produced it. **Results from different simulator or score versions are never pooled.** The current simulator is `v4`; scores `v1` through `v3` remain available so historical results stay reproducible rather than being silently rewritten.

---

## Environments

### Heat exchanger

Shell-and-tube and concentric-tube geometries, evaluated against a duty target and pressure-drop limits.

- **Tube and annulus side** use the `ht` and `fluids` libraries (Gnielinski, ε-NTU, Darcy friction).
- **Shell side** is hand-implemented Kern/Bell-Delaware, because no library covers cross-flow over tube bundles.
- The simulator also produces a cost model and a set of TEMA/ASME design checks — tube and shell velocity limits, unsupported span against the TEMA table, wall thickness against ASME UG-27, flow-induced vibration, and LMTD correction factor — each of which costs the design score.
- Where a correlation is used outside the range it was validated for, the simulator says so through `shell_correlation_in_range` and `fidelity_notes` rather than through a warning. Warnings cost score, and charging a design for the referee's own blind spots would be scoring our ignorance instead of the design.

Further environments (UAV wing, turbomachinery) are planned and the core is environment-agnostic by construction; nothing in `src/sunimuhendis/core/` is heat-exchanger-specific.

---

## Using the environments as a library

The environments are packaged so that another project — a training pipeline, an optimiser, your own benchmark — can use the referee without any of this repository's harness.

### Install

```bash
pip install "sunimuhendis[heat_exchanger] @ git+https://github.com/mfreyhan/SuniMuhendis.git@envs-v0.3.1"
```

Pin the tag. Simulator and score behaviour is versioned deliberately, and installing from a moving branch means your results stop being comparable without warning.

Extras select which environments' dependencies are pulled in, so a consumer that only needs one does not install the rest:

| Extra | Installs |
|---|---|
| `heat_exchanger` | `ht`, `fluids` |
| `all` | Every environment's dependencies |

### Evaluate a design

```python
from sunimuhendis import make_env, list_environments

print(list_environments())          # ['heat_exchanger']

env = make_env("heat_exchanger", score_version="heat_exchanger_score_v3")

task = {
    "task_id": "example",
    "score_version": "heat_exchanger_score_v3",
    "target_heat_duty": 350000.0,   # W
    "max_dp_tube": 2500.0,          # Pa
    "max_dp_shell": 2500.0,         # Pa
}

design = {
    "geometry_type": "shell_and_tube",
    "length": 5.0,
    "inner_tube_di": 0.016,
    "inner_tube_do": 0.020,
    "outer_shell_di": 0.48,
    "number_of_tubes": 200,
    "baffle_spacing": 0.5,
}

result = env.evaluate("example", task, "design-1", design)

result.status                       # 'success' | 'schema_error' | 'drc_error' | 'simulation_error'
result.score.normalized_total       # float in [0.0, 1.0]
result.score.components             # per-objective breakdown
result.metrics                      # every engineering metric the simulator produced
result.raw_simulation_output         # warnings, fidelity notes, intermediate quantities
```

`evaluate()` never raises on a bad design. A malformed or impossible design returns a result with the failing stage in `status` and a score of `0.0`, so a training loop can treat every response uniformly.

### What ships, and what does not

The wheel contains `core`, `environments`, `parsing` and `prompts` only. The benchmark harness — model clients, samplers, dashboard — stays in-tree and is excluded from the distribution, so a consumer pulls the referee and nothing else.

`prompts` ships on purpose: it lets a separate project construct exactly the same prompt used for benchmarking, so designs generated elsewhere remain comparable to the results published here.

---

## Auditing a task before you use it

A task can be badly calibrated in ways that are invisible until you have spent a great deal of money discovering them: a target no design can reach, a penalty no design can avoid, or a reward budget that pays more for producing *any* valid design than for producing a good one.

`audit_task()` answers those questions from the environment's own physics, before any model is called:

```python
report = env.audit_task(task, num_samples=20000)

report.is_healthy()        # False if any CRITICAL finding survived
report.forced_warnings     # penalties that fire for EVERY feasible design
report.entry_reward        # score for reaching any feasible design at all
report.craft_reward        # score for going from feasible to optimal
report.dead_checks         # declared design rules that can never fire
print(report.summary())
```

It is environment-agnostic by construction: the algorithm lives in `BaseEnvironment`, and each environment supplies its own design-space sampler, requirement definitions, and closed-form physical limits. A future environment audits its own physics through the same call.

This capability exists because it was needed. A full audit of the heat exchanger referee is in [`reports/simulator_v3_physics_audit.md`](reports/simulator_v3_physics_audit.md): the physics engine proved sound, but one of our own benchmark tasks turned out to be calibrated against a thermodynamic wall, with a score ceiling that was an artefact of the task rather than a measurement of any model.

---

## Benchmark harness

### Experiment tracks

Tracks are the top-level boundary under `results/`. Each task owns its prompt, its targets, and its outputs, and tasks are never shared implicitly across tracks:

```text
results/
  zero_shot/                     # active: one prompt, one response, no feedback
    <task-slug>/
      prompt.txt                 # exact text sent to the model
      task.json                  # matching targets, weights, and versions
      notes.md                   # research notes, rendered in the dashboard
      api_runs/<model>.jsonl     # automated attempts, appended per model
      manual_runs/<model>.jsonl  # manually pasted attempts
  feedback_driven/               # reserved: iterative tasks, no runner yet
```

The active benchmark is **zero-shot**: one task prompt produces one design, with no examples, no simulator feedback, and no score-guided retries. Reasoning effort is treated as an inference setting rather than a different evaluation mode, and is recorded in the model name so runs stay reproducible.

A **feedback-driven** track — generate a design, then iterate on structured simulator feedback for a bounded number of rounds — has its own task catalog and dashboard workspace but no execution code yet.

### Running a benchmark

Models are served through **OpenRouter**, which is where the model registry (`configs/benchmarks/models.json`, 437 models) points. Clients for Hugging Face Inference Providers and opencode also exist, alongside offline clients for testing the pipeline without spending anything.

```bash
# One task, one model, twenty independent attempts
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v2 --model gpt-oss-120b --repeats 20

# Pin a reasoning mode (recorded as gpt-oss-120b__reasoning-low)
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v2 --model gpt-oss-120b \
    --reasoning-effort low --repeats 20

# Check effective parameters and limits without making API calls
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v2 --model gpt-oss-120b --preflight-only

# Several tasks in one command
python scripts/run_api_benchmark.py --prompt heat_exchanger_v1,heat_exchanger_v2 --model gpt-oss-120b --repeats 20
```

Preflight clamps the output budget to the model's live limits, drops unsupported parameters, and refuses models that cannot guarantee an output-token bound. Every record stores the exact prompt, the full task parameters, and the inference parameters that produced it.

Refresh live model capabilities with `python scripts/sync_openrouter.py`.

### Cost accounting

Every run is a receipt. Each record carries token counts, the price list it ran against, and a cost with its basis — `provider_charged` when the provider reported what it billed, `price_snapshot` otherwise.

Prices are read **live** at the start of a run and frozen into the record, rather than taken from a registry that may be weeks stale. Each run also archives the price list it used, so the history needed to reprice old runs accumulates by itself.

```bash
python scripts/token_report.py --by model     # all-time ledger, by model
python scripts/token_report.py --as-of 2026-09-01 --csv spend.csv
```

### Dashboard

```bash
streamlit run scripts/dashboard.py
```

Keeps task catalogs separated by track, reads the pipeline as a funnel (responded → parsed → schema → DRC → simulated), scores requirement compliance against the task config, reports design diversity, and lets you inspect any individual run down to the raw response. Filtered data exports as CSV or JSONL.

---

## Development

Python **3.9**. Keep contributions 3.9-compatible: no `X | Y` unions, no `match`.

```bash
git clone https://github.com/mfreyhan/SuniMuhendis.git
cd SuniMuhendis

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .                  # makes `sunimuhendis` importable

pytest tests/ -v
```

API keys are read from `.env` (git-ignored; copy `.env.example`). `OPENROUTER_API_KEY` is the one you need for benchmarks.

Useful entry points:

| Command | Does |
|---|---|
| `python scripts/run_heat_exchanger.py` | Simulate a sample design end to end |
| `python scripts/run_simulation.py` | Exercise every failure path with dummy components |
| `python scripts/run_baseline.py` | Generate and evaluate designs without a model, for baselines |
| `python scripts/calibrate_hard_task.py` | Deterministic calibration report for a task |

---

## Status

**Working:** the evaluation pipeline and heat exchanger environment; LLM-free baselines; the model client interface; zero-shot benchmarks across a range of commercial and open models; full cost accounting; task feasibility auditing.

**In progress:** a harder, better-calibrated heat exchanger task, designed against the audit rather than by intuition.

**Planned:** the feedback-driven evaluation track; additional engineering environments.

**Separate and private:** training our own models against these environments.

---

## Feedback

If this framework or its benchmark results are useful in your work, please open an issue — we are interested in how the referee holds up outside our own use of it.

No license has been chosen yet, so default copyright applies: the code is readable here but not yet licensed for reuse.
