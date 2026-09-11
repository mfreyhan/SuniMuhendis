# Hard thermal/hydraulic task

This is a new, self-contained task; historical v1–v4 prompts and runs are unchanged.
It retains Score V1 and the seven design variables. Relative to v2, heat duty
increases from 150 to 350 kW and both pressure-drop limits decrease from 50 to
2.5 kPa. Weights are heat 60%, tube pressure 17.5%, shell pressure 17.5%,
effectiveness 5%, and cost 0%. The fixed 50,000 USD/year cost reward was readily
saturated, so this task deliberately tests thermal/hydraulic design, not cost.

The prompt includes numerical targets, fixed fluid conditions, and exact scoring
rules. Score V1 is a weighted soft score: meeting every target is not guaranteed
by a high score. Report simultaneous attainment of Q >= 350 kW and both pressure
drops <= 2.5 kPa alongside scores and warnings. Pipeline `success` only means
that the design could be evaluated.

Offline calibration: `python scripts/calibrate_hard_task.py` uses 3,000 seeded,
geometrically coherent shell-and-tube samples. The report and a feasible reference
design are in `reports/hard_task_calibration.json`, outside the model prompt.
2,977 simulations succeeded; 838 samples met all three targets (27.93% of all
samples). None of these were warning-free. This is a sampler-specific feasibility
check, not evidence that the task separates LLMs or a proof of the optimum.
The highest-scoring sampled design does not meet all three targets, illustrating
the difference between Score V1 and strict feasibility.

Run models through your configured OpenRouter provider, for example:

```bash
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v1 --provider openrouter --model gpt-oss-20b --repeats 20
```

Use the same repeat count and generation settings for model comparisons. Results
belong to this prompt unit and must not be pooled with the old 150 kW task.
