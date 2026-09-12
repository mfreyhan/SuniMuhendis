# SuniMuhendis (AI-Driven Engineering Design)

SuniMuhendis is an AI agent-based framework designed to explore whether Large Language Models (LLMs) can learn to generate valid and performant engineering designs using physics-based simulation feedback.

Currently, this repository contains the core simulation and evaluation pipeline (Phase 0 & Phase 1) for a **Heat Exchanger** environment. The system acts as a strict evaluator (referee) that takes structural design parameters, runs Design Rule Checks (DRC), simulates the physical outcomes, and calculates a normalized benchmark score based on predefined targets.

## Project Architecture

The pipeline consists of the following steps:
1. **Schema Validation**: Ensures the proposed design matches the required data types (via Pydantic).
2. **Design Rule Check (DRC)**: Filters out physically impossible geometries (e.g., inner diameter > outer diameter) before simulation.
3. **Physics Simulator**: Runs actual engineering calculations using libraries like `ht`, `fluids`, and `CoolProp`.
4. **Benchmark Score Calculation**: Compares the simulation metrics (e.g., heat duty, pressure drop) against the task targets and generates a normalized score between 0.0 and 1.0.

## Current Environments

- **Heat Exchanger MVP**: Simulates both `concentric_tube` and `shell_and_tube` geometries. Calculates overall heat transfer coefficient (U), heat duty (Q), and pressure drops using the NTU method.

## Installation

Use a virtual environment (Python 3.9).

```bash
# Clone the repository
git clone <repository_url>
cd SuniMuhendis

# Create & activate the venv, then install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For the automated Hugging Face benchmark (Usage Â§2) you also need an HF token:

```bash
cp .env.example .env
# then edit .env and set:  HF_TOKEN=hf_xxxxxxxx
```

The token is read from `.env` (git-ignored) automatically. Get one at
<https://huggingface.co/settings/tokens> with "Make calls to Inference Providers" permission.

## Usage

### 1. Simple Physics Evaluation
You can test the environment using the provided demo script. It loads a sample task (`task_001.json`) and a valid design (`heat_exchanger_valid_001.json`), runs the simulation, and prints the results.

```bash
python scripts/run_heat_exchanger.py
```

### 2. Automated HF Model Benchmark
Send **one prompt to many Hugging Face models in a single command**, run every response through the same `schema â†’ DRC â†’ simulation â†’ score` pipeline, and store the results. (Requires `HF_TOKEN` in `.env` â€” see Installation.)

A **prompt unit** is a self-contained folder under `results/`:

```text
results/<prompt-slug>/
  prompt.txt                # exact text sent to the model, including numerical requirements
  task.json                 # matching targets and weights for evaluation
  api_runs/<model>.jsonl     # API runs, appended per model
  manual_runs/<model>.jsonl  # manual runs
```

The benchmarks include `heat_exchanger_v1` through `heat_exchanger_v4`, the
thermal/hydraulic `heat_exchanger_hard_v1`, and `heat_exchanger_hard_v2` using
Score V3 with specification-miss penalties and a calibrated cost objective.
See the hard task's README for calibration and scoring limitations.
Each prompt uses its own adjacent `task.json`. Separate
`--task`, `--task-set`, and `--score-version` overrides are no longer supported.
When adding a new task, create a new prompt unit and keep the numerical
requirements in `prompt.txt` consistent with `task.json`.

```bash
# A single prompt:
python scripts/run_api_benchmark.py --prompt heat_exchanger_v4 --model claude-sonnet-5 --repeats 20

# Score V3 hard task:
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v2 --model claude-sonnet-5 --repeats 20

# Run-specific reasoning mode (recorded as kimi-k2.6__reasoning-none):
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v2 --model kimi-k2.6 --reasoning-effort none --repeats 20

# Validate effective limits and parameters without making API calls:
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v2 --model llama-3.3-70b-instruct --preflight-only

# Multiple self-contained prompts:
python scripts/run_api_benchmark.py --prompt heat_exchanger_v1,heat_exchanger_v2,heat_exchanger_v3,heat_exchanger_v4 --model claude-sonnet-5 --repeats 20

# Dashboard (API, manual, or combined results):
streamlit run scripts/dashboard.py
```

Models and live capability metadata are listed in `configs/benchmarks/models.json`.
Refresh OpenRouter model capabilities (including supported reasoning modes) with
`python scripts/sync_openrouter.py --no-sync`. Use the configured `name` with
`--model`. In an interactive terminal, reasoning-capable models show a numbered
mode menu. `--reasoning-effort` bypasses that menu for automated runs. The selected
mode is appended to the result model name and filename. New API records include
the exact prompt, full task parameters, and inference parameters for reproducibility.
Every run uses a shared output budget (`--max-output-tokens`, default 8192) and
temperature (`--temperature`, default 0.7). Preflight clamps the output budget to
the live model/context limits, omits unsupported temperature settings, and blocks
models that cannot guarantee an output-token bound.

The v5 canonical experiment, its separate task set, and V2-rescored copies of
older results are preserved in `archive/score_v2_experiment/`. They are excluded
from the active dashboard. Original v1–v4 results are unchanged. Score V2 is
still available explicitly through the library for research.

### 3. Manual LLM Evaluation (cloud models, by hand)

The manual evaluator reads the same `prompt.txt` and `task.json` pair as the API
runner. Paste the model response when prompted; successful results are appended
to the prompt unit's `manual_runs/` folder.

```bash
python scripts/run_llm_eval.py --client interactive --prompt heat_exchanger_v4
```

### 4. Running Tests
To run the unit and smoke tests:
```bash
pytest tests/ -v
```

## Roadmap

- **Phase 0 & Phase 1**: Core interfaces and Heat Exchanger Simulator (Completed âœ…)
- **Phase 2**: LLM-free Baseline and Dataset Generation (Completed âœ…)
- **Phase 3**: Model Client Interface and First LLM Integration (Completed âœ…)
- **Phase 4**: Small Model SFT / LoRA
- **Phase 6**: Commercial LLM Benchmarks and Advanced Environments (UAV Wing, Turbomachinery)
