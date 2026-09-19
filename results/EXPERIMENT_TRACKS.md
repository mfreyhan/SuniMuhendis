# Experiment track layout

Experiment protocols are the top-level boundary under `results/`. Each track owns
its task definitions as well as its outputs, preventing a zero-shot task from
silently becoming the definition of a feedback-driven experiment.

```text
results/
  zero_shot/
    <prompt-slug>/
      prompt.txt
      task.json
      notes.md
      api_runs/<model>.jsonl
      manual_runs/<model>.jsonl
  feedback_driven/
    <feedback-task-slug>/        # reserved; no task or runner exists yet
      prompt.txt
      task.json
      notes.md
      episodes/<model>.jsonl
```

Every task owns a Markdown `notes.md` file. The dashboard renders it with the
selected task while keeping notes isolated by experiment track.

## Zero-shot track

Each JSONL row is one independent model attempt. The model receives the task
prompt once and gets no examples, simulator feedback, score-guided retry, or
information from another attempt. Reasoning effort is an inference parameter and
does not change the experiment track.

All active API and manual runners read and write under
`results/zero_shot/<prompt-slug>/`. The dashboard still reads the former
`results/<prompt-slug>/<track>/<source>/` and
`results/<prompt-slug>/<source>/` layouts for backward compatibility, but never
writes them.

## Feedback-driven track

This top-level track is reserved for a later implementation. It intentionally has
no copied zero-shot task folders: feedback-driven tasks will define their own
prompts, scoring configuration, and strategy metadata. Its unit of comparison
will be an episode rather than an individual call. A future episode record should
preserve at least:

- a stable episode identifier, model, provider, prompt unit, and strategy version;
- the initial design and evaluation;
- every feedback round, including the exact feedback, raw response, parsed design,
  simulation result, and score;
- initial, final, and best score, score gain, stop reason, and completed rounds;
- aggregate model calls, simulator calls, prompt/output tokens, latency, and cost.

The future runner must write `evaluation_mode: "feedback_driven"` under
`results/feedback_driven/<feedback-task-slug>/`. Zero-shot and feedback-driven
results must never share task folders or JSONL files and must not be aggregated
together unless a comparison view explicitly groups by experiment track.
