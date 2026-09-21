# Library API

SuniMuhendis exposes versioned engineering environments through a small public
registry:

```python
from sunimuhendis import list_environments, make_env

list_environments()
env = make_env("heat_exchanger", score_version="heat_exchanger_score_v4")
```

Factories import simulator dependencies lazily. Installing the
`heat_exchanger` extra is therefore sufficient for consumers that only use that
environment.

## Evaluation result

`BaseEnvironment.evaluate(task_id, task_params, design_id, design_params)`
applies four stages in order:

1. schema validation;
2. design-rule checks;
3. simulation;
4. benchmark scoring.

The raw design dictionary flows through the stages after schema validation.
Invalid designs return an `EvaluationResult` with a zero score and a stage
status; they do not raise into the caller's optimization or training loop.

Successful results expose:

- `status` and `error_message`;
- `score.normalized_total` and per-objective components;
- engineering `metrics`;
- `raw_simulation_output`, including warnings and fidelity notes.

Configuration errors made by the experiment author, such as an unknown
operating-condition key, raise instead of being attributed to the design.

## Heat-exchanger tasks

Operating conditions belong to the task, not the design. A task may provide an
`operating_conditions` block and optional `secondary_operating_points`.
Secondary points evaluate the same geometry at additional conditions and retain
their metrics under `raw_simulation_output["secondary_points"]`.

The design schema contains the geometric decisions available to the model.
Task-owned flow rates, temperatures, fouling assumptions, material limits, and
targets cannot be overridden by a submitted design.

## Auditing a task

A badly calibrated task can have an unreachable target, an unavoidable warning,
or a reward budget dominated by merely reaching feasibility. Audit a task before
spending model calls:

```python
report = env.audit_task(task, num_samples=20_000)

print(report.summary())
print(report.is_healthy())
print(report.score_ceiling)
print(report.forced_warnings)
print(report.entry_reward, report.craft_reward)
```

Sampling can demonstrate that a score is reachable; it cannot prove that a
higher score is impossible. Tasks can therefore include `reference_designs` as
explicit feasibility witnesses.

The audit algorithm is environment independent. Each environment supplies broad
sampling, hard requirements, declared checks, and any closed-form physical
limits it can derive.

## Versioning

Simulator and score versions are independent. Store both with every result and
do not pool results across either boundary. Score V4 is the recommended
heat-exchanger score for new tasks; older scores remain available only to
reproduce historical experiments.

The detailed physics audit that motivated task auditing is preserved in
[the simulator V3 report](../reports/simulator_v3_physics_audit.md).
