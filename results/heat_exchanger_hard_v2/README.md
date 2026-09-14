# Hard task with Score V3

This prompt unit uses simulator V3 and `heat_exchanger_score_v3`. It is separate
from `heat_exchanger_hard_v1`; results from different simulator or score versions
must not be pooled.

Results in this prompt unit belong to the zero-shot track: one prompt, one model
response, and no simulator feedback or score-guided retry. Optional reasoning is
disabled for standard comparisons; explicitly enabled reasoning runs are separate
diagnostic variants and carry a `__reasoning-<mode>` suffix.

The task rewards heat duty (50%), tube pressure drop (17.5%), shell pressure drop
(17.5%), effectiveness (5%), and annualised cost (10%). Cost receives full raw
reward at or below 5,000 USD/year, decreases linearly, and reaches zero at 15,000
USD/year. Its reward is softly gated by the weakest thermal/hydraulic reward.

Each missed primary requirement (heat duty and the two pressure-drop limits) adds
the same 10% penalty as one simulator warning. Partial objective rewards are still
retained, so near misses remain distinguishable.

Generate the deterministic calibration report with:

```bash
python scripts/calibrate_hard_task.py --prompt heat_exchanger_hard_v2 --output reports/hard_task_v2_calibration.json
```

The seeded 3,000-design calibration produced 2,977 successful simulations and
838 designs meeting all three thermal/hydraulic requirements. Scores span
0.0651–0.7834. The highest-scoring design meets all three requirements and has
an annualised cost of 3,855 USD/year. No feasible sampled design was warning-free.

Run a model with:

```bash
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v2 --provider openrouter --model gpt-oss-20b --repeats 20
```

Reasoning effort is selected per execution and becomes part of the result model
name and filename. Omit `--reasoning-effort` in an interactive terminal to select
from the modes advertised by the synced OpenRouter metadata:

```bash
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v2 --provider openrouter --model kimi-k2.6 --reasoning-effort none --repeats 20
```

Check the effective parameters without spending API credits:

```bash
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v2 --provider openrouter --model llama-3.3-70b-instruct --preflight-only
```
