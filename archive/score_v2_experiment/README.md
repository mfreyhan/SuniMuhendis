# Archived Score V2 / canonical prompt experiment

Introduced by commit `cc310dd`. Archived while restoring the self-contained
v1–v4 benchmark workflow introduced before that commit (including `51c24f4`).

The canonical v5 prompt omitted numerical task targets. The runner selected
different task JSON files for scoring but sent the same prompt for each task.
These results therefore do not measure adaptation to those task requirements.

All original v5 runs, the separate task set, and v1–v4 `_v2_rescored.jsonl`
files are preserved here. They are outside the active dashboard's results root.
Original v1–v4 prompts, task files and original runs remain under `results/`.
Score V2 remains available in the library for explicit research use; the active
v1–v4 tasks use Score V1. Do not merge rescored copies into original run counts.
