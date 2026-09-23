# Turbomachinery throughflow environment

This environment is an experimental adapter to NASA `turbo-design`. It accepts
multi-stage axial compressor and turbine designs, uses ten streamtubes, and
requires eleven hub-to-shroud values at `0.0, 0.1, ..., 1.0` for inlet metal
angle, exit metal angle, and the physical profiles' stagger angle.

## Reproducible setup

NASA code remains an external dependency under the NASA Open Source Agreement;
it is not copied into the SuniMuhendis wheel.

```bash
python -m pip install -r requirements-throughflow.txt
python -m pip install -e .
sunimuhendis-setup-throughflow
```

The first command pins the reviewed NASA commit. The setup command downloads the
Kacker-Okapuu and Ainley-Mathieson chart data from that same commit and verifies
their SHA-256 hashes. It is available to external repositories after installing
SuniMuhendis. Simulation never accepts an unverified pickle and does not silently
download mutable data from NASA `main`.

From a separate training repository, install both repositories at immutable
revisions and run the same packaged setup command:

```bash
python -m pip install "turbo-design @ git+https://github.com/nasa/turbo-design.git@23c2b0bf781b4b030014f458ecfde872896777a2"
python -m pip install "sunimuhendis @ git+https://github.com/mfreyhan/SuniMuhendis.git@<release-tag>"
sunimuhendis-setup-throughflow
```

## Ownership boundary

The model supplies passage geometry and blade geometry: blade count, axial
chord, rotor tip clearance, trailing-edge thickness, and eleven-point inlet,
exit, and stagger-angle distributions. The benchmark task owns operating
conditions, numerical resolution, loss model, deviation model, and any
calibrated fixed loss or deviation values. This prevents a model from choosing
the referee that scores its own design.

`axial_compressor_candidate_v1` applies the NASA preliminary diffusion loss and
a corrected Carter deviation. Local pitch and solidity are derived from radius,
blade count, axial chord, and the supplied stagger at every span station. The
pinned NASA Carter implementation has a radians/degrees mismatch, so the adapter
evaluates the algebra documented in NASA's source and records this in fidelity
notes.

`axial_turbine_candidate_v1` currently uses NASA TD2 as an interim correlation.
Kacker-Okapuu and Ainley-Mathieson remain shadow candidates: the pinned backend
cannot yet run Kacker-Okapuu reliably because its pre-solve state and stator
secondary-loss calculation contain blocking defects. Turbine deviation remains
zero unless a task supplies a calibrated fixed eleven-point distribution.

Both candidate profiles return a score of zero. They become reward eligible
only after independent compressor and turbine validation cases establish error
limits for performance, spanwise flow, off-design behavior, and numerical
resolution.

The current compressor evidence, executable comparison, NASA EEE audit, and
reward-eligibility gate are documented in
[compressor_validation.md](compressor_validation.md).

## Result diagnostics

Each blade row reports total pressure and temperature, absolute and relative
Mach number, loss coefficient, solidity, applied deviation, absolute and
relative exit flow angles, metal angles, tip-clearance fraction, and
trailing-edge-to-pitch ratio. `fidelity_notes` identifies physics that remains
approximate or unavailable.
