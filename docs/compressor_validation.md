# Compressor validation status

The compressor environment can run a complete one- or two-stage axial design
through the public `make_env("turbomachinery_throughflow")` API with 11 radial
solution points (10 streamtubes). It is not yet an experimentally validated
compressor design model and remains reward-ineligible.

Run the reproducible comparison from the repository root:

```bash
python scripts/run_throughflow_compressor_benchmark.py
```

The reference case is Mattingly example 9.1 as transcribed in NASA
`turbo-design` at the pinned revision. The published example specifies one
stage, a total-pressure ratio of 1.3, the annulus, operating point, and exit
metal angles. The second stage below is a repeated-stage integration exercise,
not a published benchmark.

| Case | Achieved PR | Target PR | Polytropic efficiency | Massflow residual |
|---|---:|---:|---:|---:|
| one-stage adapter regression | 1.3177 | 1.3000 | 1.0068 | 7.58e-8 |
| one-stage candidate physics | 1.4520 | 1.3000 | 0.9961 | 5.31e-7 |
| two-stage adapter regression | 1.6858 | 1.6900 | 1.0160 | 8.98e-7 |
| two-stage candidate physics | 2.1394 | 1.6900 | 0.9949 | 2.84e-7 |

The regression path is useful only for adapter equivalence. Its efficiency
above one is physically impossible and demonstrates why zero loss cannot be a
validation model. The candidate path applies the pinned NASA preliminary
diffusion model and the corrected Carter deviation policy. It converges, but
its pressure-ratio errors are 11.7% for one stage and 26.6% for the repeated
two-stage case. The candidate also predicts zero stator loss for this design:
the upstream implementation divides its stator swirl-change term by rotor
speed, which is zero for a stator, and the resulting value clips to zero.
Incidence loss is absent. These facts block scoring and training reward.

## EEE high-pressure compressor audit

NASA CR-165558 describes a 10-stage EEE high-pressure compressor with a cruise
design pressure ratio of 22.6, corrected airflow of 53.5 kg/s, adiabatic
efficiency goal of 86.1%, and polytropic efficiency of 90.6%:
<https://ntrs.nasa.gov/citations/19850002690>.

NASA's current reconstructed EEE example is useful source material, but it is
not a ready validation case. The example itself says that the reconstructed
geometry may differ from the original hardware and that CFD matching remains
future work:
<https://github.com/nasa/turbo-design/tree/main/examples/EEE-HPC>.

At the pinned revision, the example passes 54.4 kg/s to the solver even though
the report quantity is corrected flow. With the workbook mean inlet state
(59.48 kPa, 304.76 K), 53.5 kg/s corrected corresponds to approximately
30.54 kg/s physical flow using the standard corrected-flow definition. The
unmodified example stops at the IGV because the requested flow exceeds its
choked capacity. Re-running at 30.7 kg/s clears that check but the radial-
equilibrium integration fails at rotor 2. The reconstructed EEE case therefore
stays an audited future benchmark rather than a passing test fixture.

## Acceptance gate for physical validation

A compressor physics profile can become reward-eligible only after it meets all
of these conditions:

1. A published geometry and operating point run without fixed report-derived
   row losses or deviations.
2. Overall pressure ratio and efficiency errors are reported against measured
   or independently calculated values.
3. Spanwise quantities are compared at the same radial stations where data are
   available.
4. Incidence, profile, secondary, endwall, clearance, Reynolds, and compressible
   loss effects are either modelled or declared outside the correlation range.
5. Multi-stage and 10-streamtube convergence tolerances are enforced by the
   environment rather than inferred from a solver return code.

