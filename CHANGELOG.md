# Changelog

All notable public changes are recorded here. Simulator and score behavior have
their own explicit versions; a package release does not make results from
different simulator or score versions comparable.

## [Unreleased]

### Changed

- Raised the supported runtime to CPython `>=3.12,<3.13`.
- Added Windows and Ubuntu CI with full tests, package builds, metadata checks,
  and clean-wheel consumer validation.
- Added a constrained Python 3.12 development profile.
- Clarified the public package boundary and external-consumer workflow.
- Reorganized public documentation and added citation, security, contribution,
  and third-party provenance guidance.

### Research

- Recorded Phase 0–2 investigation of NASA turbo-design at a pinned upstream
  commit.
- Kept the throughflow backend and its assets outside the distributed package
  while solver-validation and provenance gates remain open.

## [0.5.0] - 2026-09-20

- Added the audited heat-exchanger simulator V4 and Score V4 task family.
- Added multi-point evaluation, reference-design feasibility witnesses, and
  task-owned operating conditions.
- Added live price snapshots and token/cost accounting for benchmark runs.

[Unreleased]: https://github.com/mfreyhan/SuniMuhendis/compare/envs-v0.5.0...main
[0.5.0]: https://github.com/mfreyhan/SuniMuhendis/releases/tag/envs-v0.5.0
