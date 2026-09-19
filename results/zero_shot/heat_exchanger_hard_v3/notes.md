# Research notes — heat_exchanger_hard_v3

## Why this task exists

`heat_exchanger_hard_v2` could not separate a zero-shot model from a feedback-driven one, let alone from a trained one. The audit showed three reasons, and all three were in the task rather than the physics:

1. The duty target sat at 95.2% of the effectiveness ceiling the configuration can ever reach, so heat duty was a threshold with a wall behind it rather than an objective.
2. Two warnings were mathematically unavoidable for any design meeting the requirements, so every design paid a constant 20% penalty carrying no information.
3. 85% of the score weight sat on the three requirements, which pay in full the moment they are met.

The observed ceiling of 0.783 was those three facts, not a measurement of any model. `gpt-oss-120b` reached 0.7829 and a 3,000-design random sampler reached 0.7834 — the model found the only reachable corner, and so did random search.

## What to watch for in the results

**Does the score now separate reliability from engineering?** The complaint about hard_v2 was that the headline number mixed "can emit valid JSON" with "can design well". Under V4 those are cleanly separated: everything below 0.30 is a gate failure, everything above is engineering. A model's distribution should now be readable — a cluster just above 0.30 means it passes spec but builds badly; a spread up towards 1.0 means it is actually optimising.

**Do models use the optional fields at all?** Seven new fields are available and none are required. A model that ignores them inherits 0.05 m nozzles, two passes and a 1.25 pitch ratio — workable, but it gives up a real part of the pressure budget and of the cost. Whether models reach for these levers unprompted is itself a result worth recording.

**Does anyone find the narrow window?** A perfect score needs the duty met without overshooting past the F limit at 328 kW, both pressure drops inside 10 kPa, cost under 2,000 USD/yr, and zero warnings simultaneously. The reference solution runs tube-side pressure drop at 9,585 Pa against a 10,000 Pa limit and tube velocity at 0.69 m/s against a 0.5 m/s floor. Only 12 of 2,970 calibration designs managed zero warnings at all.

**Watch for overshoot.** Exceeding 250 kW earns nothing, and past roughly 328 kW it costs a warning through the F limit. Models that reflexively maximise duty should be visibly punished for it. This is the clearest single test of whether a model is reading the objective or pattern-matching "more heat is better".

## Open questions

- Is 250 kW the right target? It is 68% of the configuration ceiling, chosen to leave headroom. If models clear the gate too easily the target can rise toward 300 kW without hitting any wall — the audit stays healthy up to there.
- Is the cost band right? 2,000 to 20,000 USD/yr spans roughly the 5th to 75th percentile of feasible designs. If scores bunch at the top, tightening `cost_good` is the first knob, and the audit will say whether it creates a floor effect.
- Five design checks never fire under this configuration (shell velocity maximum, minimum approach, both ASME wall checks, TEMA minimum pitch). The wall checks are inert because thickness is derived rather than designed. Making shell thickness a design variable would revive them and add a genuine mechanical dimension — a candidate for v4.

## Methodology note

Every parameter here was selected by measurement, not intuition. `env.audit_task(task_params)` was run across sixteen combinations of duty target and pressure limit before any value was fixed; the finding that no parameter choice could fix the reward budget under Score V3 is what forced V4 to exist. The same call is what certifies this task as healthy, and `tests/test_score_v4.py` pins that certification so it cannot silently rot.
