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

## Third-party model responses

Benchmark JSONL records can contain raw responses produced by external models.
SuniMuhendis does not claim authorship of that text. The scope and reuse limits
are described in [the benchmark-data license](results/LICENSE.md). Users must
check the originating model and provider terms before reusing raw responses.

## No endorsement

Names of third-party projects identify provenance only. They do not
imply endorsement of SuniMuhendis, its simulations, benchmark results, or
derived research conclusions.
