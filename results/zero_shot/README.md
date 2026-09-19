# Zero-shot experiments

Every folder in this track is a self-contained zero-shot task. The active runners
read the task's `prompt.txt` and `task.json`, then append independent attempts to
`api_runs/` or `manual_runs/`. No model receives simulator feedback from an
earlier attempt. Task-specific observations belong in `notes.md`; the dashboard
shows that file alongside the selected task.
