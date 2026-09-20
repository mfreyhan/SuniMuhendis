# Research notes — heat_exchanger_hard_v4

## The question this task is built to answer

`hard_v3` produced a readable leaderboard, and the headline result was that
`qwen3.8-27b` — nearly the smallest model tested — led it. That is a problem for
what this benchmark is for. If a small model already matches large ones, there
is no zero-shot gap for training to close, and a trained model matching frontier
models would be a claim about nothing.

So the diagnostic question was: is heat-exchanger design too simple a domain for
this, or was `hard_v3` too simple an instance of it?

The measurement says the instance. `hard_v3` declared eighteen limits and
enforced three; the median gate-passing design ran shell velocity at 3.6% of its
limit. The domain was never the constraint — the design space had thirteen free
variables against three that bound, so there was no corner for a good designer
to find and no penalty for a careless one who happened to land inside.

`hard_v4` does not withhold anything to make this harder. Every rule, every
threshold and the entire scoring formula are still in the prompt, because a
trained model that wins by knowing a rule its competitors were not told would be
winning an information asymmetry, not a design contest. What changed is that
more of the stated rules bind at the same time.

## What to watch for in the results

**Compare against `hard_v3` run for run.** Both tasks have the same gate at the
same cost of entry (27.1% of sampled designs pass both). A model's drop from
`hard_v3` to `hard_v4` is a measurement in its own right: it is the part of the
`hard_v3` score that came from constraints being slack rather than from the
design being good.

**Does anyone size for the velocity window rather than the velocity?** This is
the single thing the task is testing. A model that picks a tube count putting
full-load velocity just above 0.5 m/s has designed for one load and will be
charged for it at turndown. The tell is `turndown_num_warnings` > 0 with
`num_warnings` at full load = 0.

**Does the cost term still discriminate?** At the `hard_v3` band every design
clean at both loads saturated it. At 600/1,800 roughly a fifth do. If scores
bunch at 1.000 the band is the first knob; if nothing clears 0.8 it is too tight.

**Random search should do much worse here.** On `hard_v3` a 3,000-design random
sampler reached 0.783 against `gpt-oss-120b`'s 0.7829 — the model and the dice
found the same corner. Under `hard_v4`, broad random sampling finds **no**
warning-free design in 6,000 tries, while a structured grid finds 566 of 3,258
gate-passers. If a model scores well here it is because it reasoned about the
velocity window, not because it landed somewhere.

## Open questions

- **Is 70% the right turndown?** It was chosen as the deepest ratio with an
  exhibited perfect design. 60% showed no forced warning either, so if models
  clear 70% easily the dial has room before the wall at 40%.
- **Should turndown also be a gate requirement?** Right now the second load only
  contributes warnings. Requiring a duty at turndown as well would tighten it
  further, but it would raise the cost of entry, which this task deliberately
  held constant so the comparison with `hard_v3` stays clean.
- **Four checks still never fire** — minimum approach, both ASME wall checks,
  TEMA minimum pitch. The wall checks stay inert while thickness is derived
  rather than designed. Making shell thickness a design variable remains the
  candidate for adding a genuinely mechanical dimension.
- The audit's sampler was corrected while building this task and now draws three
  designs in ten in velocity coordinates. Before that it chose tube counts and
  bores independently of the flow, so every limit that is a velocity window was
  invisible to it — it reported this task's ceiling as 0.593 against a true
  1.000, and reported `hard_v3`'s as 0.997 against 1.000.

## Methodology note

Every number here was measured. The claim that the operating point is not the
lever comes from sweeping flow, inlet temperature and capacity ratio and
counting binding constraints at the optimum in each case; the claim that
turndown is the lever comes from re-evaluating `hard_v3`'s ten clean designs at
reduced flow and finding all ten violated. The turndown depth was picked from
the audit table rather than chosen, and the ceiling is carried in `task.json` as
a design that attains it, so the feasibility claim rests on an exhibit rather
than on a search that happened to stop.
