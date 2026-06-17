# SuniMuhendis (AI-Driven Engineering Design)

SuniMuhendis is an AI agent-based framework designed to explore whether Large Language Models (LLMs) can learn to generate valid and performant engineering designs using physics-based simulation feedback and Reinforcement Learning (RL).

Currently, this repository contains the core simulation and evaluation pipeline (Phase 0 & Phase 1) for a **Heat Exchanger** environment. The system acts as a strict evaluator (referee) that takes structural design parameters, runs Design Rule Checks (DRC), simulates the physical outcomes, and calculates a normalized reward score based on predefined targets.

## Project Architecture

The pipeline consists of the following steps:
1. **Schema Validation**: Ensures the proposed design matches the required data types (via Pydantic).
2. **Design Rule Check (DRC)**: Filters out physically impossible geometries (e.g., inner diameter > outer diameter) before simulation.
3. **Physics Simulator**: Runs actual engineering calculations using libraries like `ht`, `fluids`, and `CoolProp`.
4. **Reward Calculation**: Compares the simulation metrics (e.g., heat duty, pressure drop) against the task targets and generates a normalized score between 0.0 and 1.0.

## Current Environments

- **Heat Exchanger MVP**: Simulates both `concentric_tube` and `shell_and_tube` geometries. Calculates overall heat transfer coefficient (U), heat duty (Q), and pressure drops using the NTU method.

## Installation

It is recommended to use a virtual environment.

```bash
# Clone the repository
git clone <repository_url>
cd SuniMuhendis

# Install the required packages
pip install -r requirements.txt
```

## Usage

### 1. Simple Physics Evaluation
You can test the environment using the provided demo script. It loads a sample task (`task_001.json`) and a valid design (`heat_exchanger_valid_001.json`), runs the simulation, and prints the results.

```bash
python scripts/run_heat_exchanger.py
```

### 2. LLM Benchmarking & Interactive Dashboard
You can evaluate LLMs (ChatGPT, Claude, etc.) interactively, prompt them with engineering tasks, and store their responses to a local database. 

```bash
# Run the interactive evaluator
python scripts/run_llm_eval.py --client interactive
```

Once you save the models' designs, you can visualize and compare their performance metrics (Heat, Cost, Pressure Drops, etc.) via the interactive Streamlit web dashboard:

```bash
streamlit run scripts/dashboard.py
```

### 3. Running Tests
To run the unit and smoke tests:
```bash
pytest tests/ -v
```

## Roadmap

- **Phase 0 & Phase 1**: Core interfaces and Heat Exchanger Simulator (Completed ✅)
- **Phase 2**: LLM-free Baseline and Dataset Generation (Completed ✅)
- **Phase 3**: Model Client Interface and First LLM Integration (Completed ✅)
- **Phase 4**: Small LLM Supervised Fine-Tuning (SFT) (Next ⏳)
- **Phase 5**: Reinforcement Learning (RL / GRPO) Training
- **Phase 6+**: Commercial Benchmarks and Advanced Environments (UAV Wing, Turbomachinery)
