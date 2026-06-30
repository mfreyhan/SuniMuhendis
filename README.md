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

For the automated Hugging Face benchmark (Usage §2) you also need an HF token:

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
Send **one prompt to many Hugging Face models in a single command**, run every response through the same `schema → DRC → simulation → score` pipeline, and store the results. (Requires `HF_TOKEN` in `.env` — see Installation.)

A **prompt unit** is a folder under `results/`:

```
results/<prompt-slug>/
  prompt.txt    # the exact text sent to the model (committed)
  task.json     # benchmark score weights + targets used for scoring (committed)
  benchmark/    # generated results — one JSON per run (git-ignored)
    <model-name>/<timestamp>.json
```

The models to test are listed in `configs/benchmarks/models.json`
(`name` = label/folder shown in the dashboard, `model` = HF model id).

```bash
# All models in models.json, 5 runs each:
python scripts/run_hf_benchmark.py --prompt heat_exchanger_v1 --repeats 5

# A single model (use the "name" from models.json, not the HF id):
python scripts/run_hf_benchmark.py --prompt heat_exchanger_v1 --model Qwen3.5-27B

# A subset:
python scripts/run_hf_benchmark.py --prompt heat_exchanger_v1 --models Qwen3.5-27B,gpt-oss-20b
```

- **Add a new prompt:** create `results/<new-slug>/prompt.txt` + `task.json` (copy `heat_exchanger_v1` as a template).
- **Add a model:** add a line to `configs/benchmarks/models.json`. A model that isn't served on HF Inference Providers just records `client_error` for that row; the run continues.

View the results in the dashboard — the **"HF Benchmark (results/)"** source shows one row per model (the **average** of all its runs for the selected prompt):

```bash
streamlit run scripts/dashboard.py
```

### 3. Manual LLM Evaluation (cloud models, by hand)
For cloud models tested one-by-one (ChatGPT, Claude, etc.): the interactive evaluator prints the prompt, you paste the model's response back, and the result is appended to `reports/benchmark_results.json`.

```bash
python scripts/run_llm_eval.py --client interactive
```

These manual results are viewable under the dashboard's **"Manuel (reports/)"** source.

### 4. Running Tests
To run the unit and smoke tests:
```bash
pytest tests/ -v
```

## Roadmap

- **Phase 0 & Phase 1**: Core interfaces and Heat Exchanger Simulator (Completed ✅)
- **Phase 2**: LLM-free Baseline and Dataset Generation (Completed ✅)
- **Phase 3**: Model Client Interface and First LLM Integration (Completed ✅)
- **Phase 4**: Small Model SFT / LoRA
- **Phase 6**: Commercial LLM Benchmarks and Advanced Environments (UAV Wing, Turbomachinery)
