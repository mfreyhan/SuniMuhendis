# Simulator V3 — Physical Accuracy and Task Calibration Audit

**Date:** 2026-09-18
**Scope:** `simulator.py` V3, `drc.py`, `score.py` (V3), `results/zero_shot/heat_exchanger_hard_v2/task.json`
**Method:** Analytical derivation + batch simulation of ~410,000 designs (random and directed sampling)
**Conclusion:** There is **no** catastrophic error in the physics engine. The catastrophic problem is in **task calibration**: `hard_v2`'s parameter choice creates a fixed penalty no design can escape and a duty ceiling no design can exceed.

---

## 1. Verified findings (the physics engine is sound)

| Check | Method | Result |
|---|---|---|
| Energy balance | Q from ε-NTU compared with U·A·F·LMTD | Deviation **0.00%** |
| Second law | ε and Q/Q_max over 4,000 random designs | **No** violations; ε never exceeded the configuration limit |
| ε-NTU ↔ LMTD-F consistency | Two independent calculation paths | They agree |
| `ht` library call | `effectiveness_from_NTU(subtype="S&T", n_shell_tube=1)` | Works; does **not** drop into a silent fallback |
| Wall conduction | `ln(do/di) / (2πkLN)` | Cylindrical conduction is correct |
| Library boundary | `ht`/`fluids` only for in-tube flow, shell side hand-coded Kern | Correct split |

None of the findings below is therefore a case of "the equation is wrong"; all of them are **calibration and design-space** problems.

---

## 2. CATASTROPHIC — `hard_v2` is calibrated at an unreachable point

### 2.1. The duty target sits at 95% of the configuration's thermodynamic ceiling

The schema does not expose `tube_passes`; the default is `DEFAULT_TUBE_PASSES = 2`. Every design is therefore necessarily a **1 shell – 2 tube pass** TEMA E. Because the flow rates are equal, `Cr = 0.99809`, and the asymptotic ceiling of this configuration is fixed:

```
ε_max = 2 / (1 + Cr + sqrt(1 + Cr²)) = 0.586346          (NTU → ∞)
Q_max,config = ε_max · C_min · ΔT = 367,815 W
```

The task target is **350,000 W** — **95.2%** of the absolute ceiling.

| NTU | ε | Q (W) |
|---:|---:|---:|
| 1.0 | 0.4629 | 290,402 |
| 2.0 | 0.5573 | 349,571 |
| 2.5 | 0.5721 | 358,860 |
| 3.0 | 0.5793 | 363,408 |
| 5.0 | 0.5859 | 367,554 |
| ∞ | 0.5863 | 367,815 |

The target is crossed between NTU 2 and 3; **beyond NTU 3, no added area increases duty.** For comparison, pure counterflow at NTU = 5 would give ε = 0.834. The heat-transfer target is therefore not an optimisable objective; it is a threshold followed immediately by a wall.

### 2.2. Two warnings are mathematically unavoidable — every feasible design takes a fixed ×0.8

**(a) The `F < 0.75` warning.** Because flow rates and inlet temperatures are fixed, the outlet temperatures — and therefore the LMTD correction factor F — are **a function of Q alone**. No geometric freedom can affect F:

```
F = 0.75  <=>  Q = 328,436 W
task target 350,000 W  =>  F <= 0.625, always
```

Meeting the duty requirement **guarantees** this warning.

**(b) The `Tube velocity < 0.5 m/s` warning.** The nozzle diameter is fixed at the default `D_nozzle_hot = 0.05 m` and is not in the schema. The nozzle loss alone is **1,668 Pa**, i.e. **66.7%** of the 2,500 Pa budget, leaving 832 Pa. The tube-side header loss alone is `4·N_pass·ρv²/2 = 3,887·v²`:

```
even with ZERO friction    v_tube < 0.4626 m/s
MIN_TUBE_VELOCITY = 0.50 m/s
```

So the `ΔP <= 2500 Pa` constraint and `v >= 0.5 m/s` are **mutually exclusive**.

**Empirical confirmation.** Across three independent sweeps — 60,000 random, 200,000 directed (tube velocity forced into 0.4–3.2 m/s), and 150,000 `concentric_tube` — designs meeting all three requirements always carried **exactly 2** warnings; no sample showed 0 or 1. In the directed sweep, with tube velocity forced into the healthy range, **none of 190,809 valid simulations** met all three requirements.

Result:

```
penalty_factor = 0.8  (fixed for every feasible design)
score ceiling  = 0.9786 × 0.8 = 0.7829
```

This matches the observed values exactly:

| Source | Best score |
|---|---:|
| 3,000-design calibration sweep | 0.7834 |
| `gpt-oss-120b__reasoning-low` (n=20) | 0.7829 |
| `nex-n2.5-pro__reasoning-none` (n=20) | 0.7834 |

### 2.3. The stated constraint does not match the real constraint

The prompt says "ΔP <= 2,500 Pa". What the model actually has to meet is **geometric ΔP <= 832 Pa (tube) / 876 Pa (shell)** — the rest is a fixed nozzle loss the model can neither see nor change. As posed, the task is both unsolvable and unlearnable.

---

## 3. Is the ×0.8 multiplier universal? — No, it is specific to `hard_v1`/`hard_v2`, and on a knife edge

Both triggers are functions of the task parameters, and `hard_v2` is on the wrong side of both — by a **hair's breadth**:

| Task | Target duty | ΔP limit | Forced warnings | Penalty ceiling |
|---|---:|---:|---|---:|
| `hard_v1`, `hard_v2` | 350,000 W | 2,500 Pa | `F<0.75`, `v_tube<0.5` | **0.80** |
| `v1`, `v3` | 150,000 W | 50,000 Pa | — | **1.00** |

**The cliff edge — ΔP limit (target fixed at 350 kW):**

| ΔP limit | Nozzle share | Reachable v_tube | Status |
|---:|---:|---:|---|
| 2,500 Pa | 66.7% | 0.463 m/s | **forced warning** |
| 3,000 Pa | 55.6% | 0.585 m/s | free |
| 5,000 Pa | 33.4% | 0.926 m/s | free |
| 10,000 Pa | 16.7% | 1.464 m/s | free |

**The cliff edge — target duty (F = 0.75 threshold at 328,436 W):**

| Target duty | Status |
|---:|---|
| 320,000 W | free |
| 328,436 W | threshold |
| 340,000 W | **forced F warning** |
| 350,000 W | **forced F warning** |

Raising the ΔP limit from 2,500 to 3,000 Pa, or lowering the target from 350 to 325 kW, would each on its own remove both forced penalties. The problem is not structural; it is **parameter choice**.

---

## 4. Model discrimination — what does the current score measure?

All runs on `hard_v2` (n >= 20):

| Model | n | Valid | Mean (all) | Mean (valid) | Max | sd (valid) |
|---|---:|---:|---:|---:|---:|---:|
| gpt-oss-120b (low) | 20 | 85% | 0.637 | 0.750 | 0.783 | 0.082 |
| qwen3.8-27b (none) | 20 | 90% | 0.443 | 0.492 | 0.720 | 0.152 |
| deepseek-v4-flash (none) | 20 | 100% | 0.409 | 0.409 | 0.724 | 0.189 |
| nex-n2.5-pro (none) | 20 | 75% | 0.252 | 0.336 | 0.783 | 0.190 |
| gpt-oss-20b (low) | 20 | 45% | 0.205 | 0.455 | 0.625 | 0.181 |
| llama-3.3-70b | 20 | 10% | 0.040 | 0.403 | 0.492 | 0.090 |

The headline metric (mean total reward) mixes two separate abilities into one number:

- **Compliance:** can it produce valid JSON that passes DRC? (range: 10% – 100%)
- **Engineering:** how good is the design it produces? (range: 0.336 – 0.750)

Correlations: `corr(validity, headline) = 0.83`, `corr(design quality, headline) = 0.76`. The headline is roughly the average of the two, and a model can rise to the top on **reliability** alone (see deepseek-v4-flash: 100% valid, but among the lowest design quality).

**Distribution of the reward budget — the real fairness problem.** In an 80,000-design sweep:

```
invalid answer (0.0)   ->  worst feasible design :  +0.439 points
worst feasible         ->  theoretical optimum   :  +0.256 points
```

Score distribution of feasible designs: p5 = 0.528, median = 0.616, p95 = 0.746, ceiling = 0.783 (sd = 0.068).

**The score rewards showing up, not doing engineering.** This directly blocks the research question: feedback-driven iteration can only improve the second (0.256) interval, and that interval is narrower than the first. The `zero-shot < feedback-driven < trained model` ladder cannot be measured on this task.

---

## 5. Secondary findings (not catastrophic, but they affect the v3 design)

| # | Finding | Effect |
|---|---|---|
| 5.1 | The Kern Nu correlation is used below its validity range (`Re_shell ≈ 1,000` in realistic designs, Kern valid for >= 2,000); at `Re < 10` it is extrapolated with `abs(Re)` | `h_o` optimistic |
| 5.2 | The `P_design` default is 101,325 Pa (atmospheric) → **both ASME wall-thickness checks are dead code**. They did not fire once across 22,457 designs. The nozzle-velocity, pitch-ratio and minimum-approach checks likewise never fire | Half of the design checks are inert |
| 5.3 | Operating cost is **0.32%** of annualised cost (total pumping power 13.6 W) → cost is effectively steel mass | The "pay pumping power for compactness" trade-off does not exist |
| 5.4 | Hot-fluid properties are frozen at 80 °C water; they are not updated even if `T_hot_in` changes | Wrong at off-nominal temperatures (currently no effect, as existing tasks use the default) |
| 5.5 | `drc.py` **hardcodes** `tube_passes=2` / `pitch_ratio=1.25` / `pitch_type=square` and ignores the design's own values; the simulator uses the real values | A design with `tube_passes=4` passes DRC and then fails in the simulator with `simulation_error`. **This bites immediately if the schema is widened in v3.** |
| 5.6 | Shell-side `A_cross` does not depend on `N_tubes` at all (classic Kern assumption) | Sparse bundle in a wide shell → `h_o` overestimated |
| 5.7 | `schema.py` uses `extra="forbid"` → the ~20 optional parameters the simulator reads via `dict.get(...)` (`tube_passes`, `pitch_ratio`, `baffle_cut`, `D_nozzle_hot`, `m_dot_hot`, ...) are **unreachable from any LLM design**; they are rejected at the schema stage | The design space really is only 7 fields; these parameters are dead from the benchmark's point of view. *(Note: the statement in `CLAUDE.md` that "extra fields beyond the schema are preserved and used downstream" is therefore wrong and should be corrected.)* |
| 5.8 | `concentric_tube` breaks the ε ceiling because it is counterflow (reaching 538 kW), but its best score is 0.761 and it needs an 80 m tube (`L/D = 421`) | Not a real escape route; does not change the 0.783 ceiling |

---

## 6. Implications for `hard_v3`

The operational conclusion of the audit: **the first job in v3 is not to add difficulty but to open up headroom.** In order of priority:

1. **Either expose the nozzle size in the schema or remove it from the ΔP score.** Having 66% of the ΔP constraint be a constant the model cannot touch makes the task unsolvable and the measurement meaningless.
2. **Expose `tube_passes` in the schema** (or unbalance the flows to move `Cr` away from 1). Either lifts the ε ceiling and makes duty an optimisable objective again. **Item 5.5 must be fixed** before widening the schema, otherwise DRC and the simulator disagree.
3. **Make the target duty and the warning thresholds consistent.** Meeting a requirement must not force a warning; warnings should be avoidable, not a fixed tax.
4. **Redistribute the reward budget.** The ratio between "producing a valid design" and "producing a good design" is currently 0.44 / 0.26. It needs to be reversed so that iteration and training can produce measurable gains.
5. **Separate the two axes in reporting.** Validity rate and valid-design quality should be reported separately; a single headline average does not discriminate between models fairly.

---

## 7. Fixes made after the audit (Simulator V4, package 0.3.0)

The following were fixed in response to this audit. **The simulator version was raised from `v3` to `v4`:
outputs changed, and V3 and V4 results must never be pooled.**

### Fixed

| Finding | Change | Effect |
|---|---|---|
| 5.5 — DRC hardcoded `tube_passes`/`pitch_ratio`/`pitch_type` | `drc.py` now reads these values from the design itself; DRC checks that the pass count is even, divides the tube count, and meets the TEMA minimum pitch ratio | No behaviour change (the schema accepts no extra fields), but **required before widening the schema in v3** |
| Fixed `MAX_UNSUPPORTED_SPAN = 1.5 m` | TEMA RCB-4.52 table keyed by tube OD (`max_unsupported_span()`); diameters between table entries take the limit of the smaller entry | **Warning count changed for 15.5% of designs**, score shift −0.098…+0.096, mean ≈ 0 |
| Sign error in the ASME wall-thickness formula | Switched to the UG-27(c)(1) form: `t = P·R/(S·E − 0.6·P)`; added a joint-efficiency parameter `E` (default 1.0) | No change in warnings at the default atmospheric pressure; no longer unsafe at high pressure |
| 5.1 — Kern correlation outside its validity range | `shell_correlation_in_range` metric + `raw_data["fidelity_notes"]` | Does **not** affect the score (see the note below) |
| 5.6 — Kern `A_cross` ignores bundle fill | `bundle_fill_fraction` metric + a note when fill is below 70% | Does **not** affect the score |

**Why fidelity notes do not go into `warnings`:** the score deducts 10% per warning. A design falling outside our
correlation's validity range is not a flaw in the design; it is a limit of *our* model. Counting it as a warning
would charge the referee's ignorance to the design, so these are reported through a separate channel.

### Deliberately not fixed

| Finding | Reason |
|---|---|
| 5.4 — Fluid properties fixed at 80 °C | Evaluating properties at the mean bulk temperature would rewrite every thermal result. The gain is marginal and the risk high; and since the schema allows no temperature input, it has no effect on the benchmark path. Recorded as a known limitation. |
| 5.2 — ASME checks are dead | The formula is fixed, but the checks still do not fire: **wall thickness is not designed, it is derived** (`max(6 mm, D/200)`). The only way to bring them to life is to add thickness to the schema as a design variable — a v3 task decision. |
| 5.3 — Operating cost is negligible | This is not a physics error but a weighting/task-design issue. Making the ΔP–cost trade-off meaningful belongs to v3's reward-budget decision. |

### Audit tool

To make the findings reproducible, `BaseEnvironment.audit_task()` was added — an environment-independent
template method in which each environment supplies its own physics through `analyse_physics()`. Every number in
sections 2, 3 and 4 of this report can be regenerated with a single call:

```python
from sunimuhendis import make_env
env = make_env("heat_exchanger", score_version="heat_exchanger_score_v3")
print(env.audit_task(task_params).summary())
```

`tests/test_task_audit.py` pins both that the walled task is flagged and that a task with genuine headroom is
**not** flagged. `tests/test_simulator_v4_fixes.py` pins each of the fixes above individually.
