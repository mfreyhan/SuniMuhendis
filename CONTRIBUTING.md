# Contributing

Thank you for improving SuniMuhendis. Contributions should preserve the
credibility of the evaluator: behavior must be reproducible, versioned, and
supported by engineering evidence.

## Set up the project

Use CPython 3.12 and follow [the development guide](docs/development.md). Before
opening a pull request, run:

```bash
python -m pip check
python -m pytest tests/ -q
python -m build
python scripts/check_wheel_metadata.py dist
python scripts/check_wheel_consumer.py dist
```

## Contribution rules

- Keep schema, DRC, simulation, and scoring responsibilities separate.
- Preserve deterministic behavior within the pinned runtime.
- Add a simulator or score version when numerical behavior changes.
- Do not rewrite historical benchmark records to a newer version.
- Explain the physical basis and validity range of new correlations.
- Treat task configuration mistakes as experiment-author errors, not failed
  designs.
- Do not add third-party source, model assets, or datasets without documented
  provenance and redistribution terms.
- Keep public APIs usable from an installed wheel outside the repository.

Documentation-only changes should run link and packaging checks where relevant.
Physics changes need focused regression tests and evidence that the test would
fail under the previous behavior.

## Pull requests

Describe the concrete problem, resulting behavior, simulator/score version
impact, and validation performed. Keep generated logs and large raw artifacts
out of the pull request unless they are required reproducibility evidence.

By submitting a contribution, you agree that your contribution is licensed
under the repository's Apache-2.0 license and that you have the right to provide
it under those terms.
