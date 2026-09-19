# heat_exchanger_hard_v3 — gated optimisation

Simulator **v4**, score **heat_exchanger_score_v4**. Results here must not be pooled with any earlier task: both the simulator and the score changed.

This task exists because [`reports/simulator_v3_physics_audit.md`](../../../reports/simulator_v3_physics_audit.md) showed that `heat_exchanger_hard_v2` could not measure what the project is trying to measure. Its duty target sat at 95% of the effectiveness ceiling the configuration can reach, two warnings fired for every design that met the requirements, and its observed score ceiling of 0.783 was an artefact of those two facts rather than a property of any model.

## What changed, and why

**The reward budget is inverted.** Under Score V3, 85% of the weight sat on the three requirements, which pay in full the instant they are met. Across sixteen parameter settings the score for merely reaching a feasible design never moved off 0.439 — a structural property of the weighting, not something better targets could fix. V4 makes the requirements a gate worth 0.30, and puts the remaining 0.70 where it can always be improved.

| | hard_v2 (Score V3) | hard_v3 (Score V4) |
|---|---:|---:|
| Reward for reaching any feasible design | 0.439 | **0.300** |
| Reward for perfecting it | 0.536 | **0.700** |
| Ratio | 1.22 | **2.33** |
| Score ceiling | 0.783 | **1.000** |
| Unavoidable warnings | 2 | **0** |

**Effectiveness is no longer scored.** With the flows and inlet temperatures fixed, `Q_max` is a constant, so effectiveness is exactly `heat_duty / 627300`. Measured across 4,353 designs the correlation with duty is 1.0000000000. Every earlier score rewarded both, which paid twice for one quantity and handed the quality term a free floor. Quality is now carried by annualised cost, which is genuinely unbounded, and by warning-freedom, which is uncorrelated with cost (r = 0.007) and so is a second thing to be good at rather than something tradeable against the first.

**The duty target stands clear of the wall.** 250 kW is 68.0% of the 367,815 W ceiling of the forced one-shell-pass, two-tube-pass configuration, against 95.2% in hard_v2. Duty is an objective again rather than an asymptote.

**The pressure budget is mostly the designer's.** Nozzle bore is now a design field, so the fixed loss that consumed 66.7% of hard_v2's 2.5 kPa limit is 16.7% of this task's 10 kPa limit, and is a choice rather than a tax.

**The design space is wider without being harder to enter.** Seven required fields, unchanged. Seven optional ones — tube passes, pitch ratio, pitch type, baffle cut, both nozzle bores, material — each defaulting to the previous behaviour. Making them required would have raised the cost of producing *any* valid design, which is the opposite of what this task is for.

## Calibration

`python scripts/calibrate_hard_task.py --prompt heat_exchanger_hard_v3 --output reports/hard_task_v3_calibration.json`

Of 2,970 successful simulations, 2,335 met all three requirements and **12 did so without a single warning**. Scores span 0.060 to 1.000, with quartiles at 0.469 / 0.697 / 0.792 and the 90th percentile at 0.894.

## Feasibility audit

`reports/hard_task_v3_audit.json`, regenerable with `env.audit_task(task_params)`:

- **Healthy** — no critical findings.
- Reward budget: entry +0.300, craft +0.700.
- Score ceiling 1.000, and the fewest warnings any feasible design achieved is **0**, so a perfect score is genuinely reachable.
- No forced warnings: no penalty is unavoidable.
- Target duty is 68.0% of the configuration ceiling.

A deliberate search found a clean 1.000: 94 tubes of 12.7 mm outside diameter, 3.83 m long in a 0.296 m shell, triangular pitch at 1.283, 42.5 mm nozzles — 277 kW at 9,585 Pa tube-side, 896 USD/yr, zero warnings. It threads several limits at once, which is the point.

Five declared checks never fire under this configuration: shell velocity maximum, minimum approach temperature, both ASME wall thickness checks, and the TEMA minimum pitch. The wall checks are inert because thickness is derived rather than designed, and the pitch check because the schema already enforces the 1.25 minimum. These are known and documented in the audit report, not oversights.

## Running it

```bash
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v3 --model gpt-oss-120b --repeats 20
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v3 --model gpt-oss-120b --preflight-only
```

This is a zero-shot task: one prompt, one response, no simulator feedback and no score-guided retry. Reasoning effort is an inference setting and is recorded in the model name when selected explicitly.
