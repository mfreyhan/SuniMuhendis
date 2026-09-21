# Third-party software and research provenance

This document separates SuniMuhendis-owned code and data from third-party
software, model output, and research inputs. It is an engineering provenance
record, not a replacement for the license terms supplied by each upstream
project.

## Distributed Python package

The SuniMuhendis wheel contains project-authored modules under
`src/sunimuhendis/` and the `LICENSE` and `NOTICE` files. It declares
third-party dependencies but does not copy their source trees into the wheel.

The core package depends on `pydantic` and `json-repair`. The
`heat_exchanger` extra adds `ht` and `fluids`. The benchmark application
uses additional dependencies listed in `pyproject.toml` and
`requirements.txt`. The authoritative license for each dependency is the
license included with its installed distribution or upstream source.

## NASA turbo-design

Phase 0–2 research used NASA's
[turbo-design](https://github.com/nasa/turbo-design) at the pinned commit:

```text
23c2b0bf781b4b030014f458ecfde872896777a2
```

The upstream README refers to NASA Open Source Agreement 1.3, but the selected
checkout and generated wheel did not provide complete license metadata or a
redistributable license file for every source and data asset examined. The
research therefore applies the following boundary:

- NASA source code is not copied into this repository or SuniMuhendis wheels.
- NASA example files and serialized loss tables are not copied into this
  repository or SuniMuhendis wheels.
- No `throughflow` package extra or production environment is published.
- Research scripts require a separately obtained, pinned checkout.
- Research records identify the upstream commit, source example, and hashes.
- A completed solver call is not represented as NASA certification or
  endorsement.

Project-authored probe records contain execution metadata and computed numerical
results. Some records also retain numerical arrays emitted while running pinned
upstream examples. Those source-derived fields are research evidence; they are
not offered as reusable NASA geometry or loss-table assets, and the project's
CC BY grant does not extend any rights the project does not own.

Before distributing a throughflow backend, fork, patch, example, or data asset,
the project must obtain and ship authoritative license/copyright material,
record modifications and source hashes, and review each asset's provenance.
The open gates are tracked in
`reports/throughflow_phase_0_2/README.md`.

## Third-party model responses

Benchmark JSONL records can contain raw responses produced by external models.
SuniMuhendis does not claim authorship of that text. The scope and reuse limits
are described in [the benchmark-data license](results/LICENSE.md). Users must
check the originating model and provider terms before reusing raw responses.

## No endorsement

The names NASA and third-party projects identify provenance only. They do not
imply endorsement of SuniMuhendis, its simulations, benchmark results, or
derived research conclusions.
