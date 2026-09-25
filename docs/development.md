# Development and release workflow

## Runtime

The supported interpreter is CPython 3.12; `.python-version` pins the
development patch release. The package declares `>=3.12,<3.13`.

Create and install the development environment on Linux or macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c constraints/python312.txt -r requirements.txt -e .
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
. .venv\Scripts\Activate.ps1
python -m pip install -c constraints\python312.txt -r requirements.txt -e .
```

`constraints/python312.txt` pins the validated direct development profile. It
is not a cross-platform, hash-locked dependency file.

## Verification

```bash
python -m pip check
python -m pytest tests/ -q
python -m build
python scripts/check_wheel_metadata.py dist
python scripts/check_wheel_consumer.py dist
```

The clean consumer check creates a temporary virtual environment, installs the
wheel with only the heat-exchanger extra, changes to a directory outside the
repository, and exercises the public API with isolated imports.

GitHub Actions runs the same test, build, metadata, and consumer checks on
Windows and Ubuntu.

## Useful entry points

| Command | Purpose |
|---|---|
| `python scripts/run_heat_exchanger.py` | Evaluate the sample design |
| `python scripts/run_simulation.py` | Exercise every pipeline failure stage |
| `python scripts/run_baseline.py` | Generate and evaluate non-model baselines |
| `python scripts/calibrate_hard_task.py` | Audit a task's feasible design space |
| `python scripts/token_report.py` | Report token use and spend |

## Documentation site

The site at <https://suni-muhendis.github.io/sm-bench/> is built from `docs/`
with MkDocs Material and deployed by the `docs` workflow on every push to
`main`. Only pages listed in the `nav` of `mkdocs.yml` are published. The
leaderboard is computed from `results/` at build time, so new benchmark runs
appear after the next push.

To preview it locally, install the pinned site dependencies in a separate
environment and run:

```bash
python -m pip install -r requirements-docs.txt
python scripts/build_site_data.py
python -m mkdocs serve
```

## Release checklist

1. Update `CHANGELOG.md`, `pyproject.toml`, `CITATION.cff`, and public docs.
2. Run the full verification sequence above.
3. Confirm Windows and Ubuntu CI on the exact commit.
4. Tag the environment release with the chosen package version, for example
   `envs-vX.Y.Z`.
5. Create a GitHub Release describing simulator, score, runtime, and data changes.
6. Install the tagged wheel from a clean external environment.

New simulator or score behavior requires a new version boundary. Historical
result files are never rewritten to look as though they were produced by a
newer referee.
