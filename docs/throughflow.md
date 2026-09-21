# Turbomachinery throughflow research

SuniMuhendis is evaluating NASA's
[turbo-design](https://github.com/nasa/turbo-design) as a possible throughflow
backend. The target is a real environment that can represent simple and
multi-stage machines, multiple streamlines, empirical loss models, and multiple
operating points through the same public evaluation contract as the
heat-exchanger environment.

## Current status

Phase 0–2 research is complete at upstream commit
`23c2b0bf781b4b030014f458ecfde872896777a2`. Python 3.12 imports and the
upstream test suite work, and selected single- and multi-stage examples return
results. The research also found unresolved loss-model, convergence, mutable
state, asset, and provenance issues.

The backend is therefore **research-only**:

- it is not registered by `make_env()`;
- no `throughflow` installation extra exists;
- NASA source code, examples, and loss-table assets are not included in the
  SuniMuhendis repository or wheel;
- completed solves are not treated as physically validated training rewards;
- moving upstream branches and silent model fallbacks are prohibited.

## Distribution gate

A public throughflow environment requires all of the following:

1. authoritative license and copyright material for every distributed NASA
   source or asset;
2. pinned source, dependency, and data hashes;
3. validated empirical loss paths for the supported machine classes;
4. explicit mass-flow, energy, radial-equilibrium, and efficiency acceptance;
5. deterministic fresh-state execution and reproducible multi-point behavior;
6. clean external consumption from the training repository.

Until those gates close, only the project-authored adapter design and research
evidence may advance. See [THIRD_PARTY.md](../THIRD_PARTY.md) for the provenance
boundary.

## Evidence

- [Phase 0–2 research report](../reports/throughflow_phase_0_2/README.md)
- [Capability matrix](../reports/throughflow_phase_0_2/capability_matrix.md)
- [Requirements traceability](../reports/throughflow_phase_0_2/requirements_traceability.md)
- [Phased implementation plan](../reports/turbomachinery_throughflow_implementation_plan.md)

The detailed reports are historical engineering records and are currently
written in Turkish. This page is the maintained English public summary.
