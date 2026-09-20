# heat_exchanger_hard_v4 — one design, two loads

Simulator **v4**, score **heat_exchanger_score_v4**. The score function and the
simulator are unchanged from `heat_exchanger_hard_v3`; what changed is the task.
Results must still not be pooled across the two, because the designs are being
asked a different question.

`hard_v3` stays as the control. It is the same physics, the same score and the
same full disclosure, differing only in that it evaluates one load. Running both
and comparing is the measurement this task exists for.

## Why this task exists

`hard_v3` worked — it separated models and its ceiling was reachable. But it was
solvable by satisfying **three constraints out of eighteen**. Measured over its
own gate-passing designs, each declared limit's utilisation (1.0 = exactly
binding):

| Limit | Median utilisation | |
|---|---:|---|
| Tube velocity ≥ 0.5 m/s | 1.18 | live |
| Annualised cost | 1.01 | live |
| F ≥ 0.75 | 0.90 | live |
| Duty ≥ 250 kW | 0.82 | live |
| **ΔP tube ≤ 10 kPa** | **0.27** | slack |
| TEMA unsupported span | 0.27 | slack |
| Minimum approach ≥ 5 °C | 0.16 | slack |
| Shell velocity ≤ 2.0 m/s | 0.036 | slack |
| Vibration ≤ 0.8·v_crit | 0.025 | slack |

Both pressure limits — two of the three gate requirements — never exceeded 68%
of budget in any design that passed. Shell velocity ran at 3.6% of its limit and
vibration at 2.5%. With thirteen design variables against three binding
constraints the problem is under-determined: a design can satisfy it while
leaving almost everything else slack, and there is no corner to find.

**The operating point is not the fix.** Flow was swept to 4.8×, inlet
temperature to 150 °C, and the capacity ratio unbalanced from 1.00 to 0.20.
None lifted the count of binding constraints above three of fourteen, and inlet
temperature turned out to change nothing at all — the problem is dimensionless,
so raising both temperatures rescales every quantity and moves no limit.

## What does fix it

Requiring the same design to work at a second load. Of the ten sampled designs
that met every requirement at full load **with no warnings at all**, ten raised
at least one at reduced flow.

Velocity is proportional to flow and has a floor for fouling and a ceiling for
erosion, so a design sized for one flow is not sized for another. The window
that was slack in `hard_v3` — anywhere between 0.5 and 3.0 m/s — becomes a band
whose width is fixed by the turndown ratio. This is why real exchangers are
sized for a velocity range rather than a velocity.

## What changed, precisely

**The gate is unchanged.** The three requirements are still checked at full load
only, and still worth 0.30. The cost of producing *any* feasible design is
identical to `hard_v3` — measured at 27.1% of sampled designs for both tasks.
Only quality got harder.

**Warnings are counted at both loads.** `num_warnings` is the sum, and the
turndown contribution is reported separately as `turndown_num_warnings`.
Score V4 needed no change: it already reads `num_warnings`.

**The cost band is tighter: 600 / 1,800 USD/yr, from 2,000 / 20,000.** At the old
band **100%** of designs that were clean at both loads saturated the cost term,
which would have collapsed the score back to one dimension — "are you clean?".
At 600, about 20% saturate and the rest spread.

## Calibration

Turndown depth is a dial, and it was measured rather than chosen:

| Turndown | Fewest warnings reachable | Forced warnings |
|---:|---:|---|
| none (`hard_v3`) | 0 | none |
| 80% | 0 | none — too gentle to bite |
| **70%** | **0** (by construction) | **none** |
| 60% | 1 sampled | none |
| 50% | 2 sampled | none |
| 40% | 3 sampled | **1 — a wall** |

At 40% the tube-velocity floor becomes unavoidable: full-load velocity would
have to exceed 1.25 m/s, and the tube count that buys it cannot also buy the
area the duty target needs inside the pressure budget. That is exactly the
`hard_v2` pathology, and the audit reports it.

70% was chosen because a design reaching a **perfect 1.000** there is exhibited,
not assumed.

## Feasibility audit

`reports/hard_task_v4_audit.json`, regenerable with `env.audit_task(task_params)`:

- **Healthy** — no critical findings.
- Reward budget: entry +0.300, craft +0.700.
- Score ceiling **1.000**, attained by the reference design carried in `task.json`.
- No forced warnings: no penalty is unavoidable.
- Target duty is 68.0% of the configuration ceiling, as in `hard_v3`.

**The ceiling is proven by a witness, not by sampling.** `task.json` carries a
`reference_designs` entry, and the audit reports a critical finding if it fails
to do what it is offered to prove. Sampling can show a score is reachable and
can never show that it is not, so a ceiling measured only by sampling is a lower
bound — this task's was reported as 0.593 before the witness was added.

The witness: 86 tubes of 12.7 mm outside diameter, 2.8 m long in a 0.22 m shell,
triangular pitch at 1.283, 46 mm nozzles. 250 kW at 8.4 kPa tube-side and 552
USD/yr at full load; 193 kW at 70% turndown; **zero warnings at either load**.
Tube velocity runs 0.75 m/s at full load and 0.52 m/s at turndown against a 0.50
floor — the turndown margin is 4%, which is the point.

Four declared checks never fire: minimum approach temperature, both ASME wall
checks and the TEMA minimum pitch. Unchanged from `hard_v3` and documented there.

## Running it

```bash
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v4 --model gpt-oss-120b --repeats 20
python scripts/run_api_benchmark.py --prompt heat_exchanger_hard_v4 --model gpt-oss-120b --preflight-only
```

Zero-shot: one prompt, one response, no simulator feedback and no score-guided
retry. The prompt states the turndown load, that every limit is checked at both,
and the complete scoring formula — nothing is withheld. The task is harder
because more constraints bind at once, not because less was said.
