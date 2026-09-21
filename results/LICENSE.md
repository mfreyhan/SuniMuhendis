# License for benchmark data

Copyright 2026 Mehmet Fatih Reyhan and Ertuğrul Şahin

The source code in this repository is licensed under the Apache License, Version 2.0 (see [`LICENSE`](../LICENSE)). Benchmark data is not source code, so it is licensed separately, as described here.

## What we license

The benchmark and report material identified below that we produced is licensed under the
**[Creative Commons Attribution 4.0 International License (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)**.

This grant covers the following project-authored or project-computed material:

- task definitions (`task.json`) and prompts (`prompt.txt`)
- evaluation output for every run: scores, score components, engineering metrics, simulator warnings, fidelity notes, status and error fields, token counts, latency, pricing snapshots and costs
- research notes (`notes.md`), track documentation, and the engineering reports under `reports/`

It does not replace the Apache-2.0 license for source code, and it does not apply
to third-party material merely because that material is stored in this
repository. Third-party research provenance is documented in
[`THIRD_PARTY.md`](../THIRD_PARTY.md).

You are free to share and adapt this material, including commercially, provided you give appropriate credit, link to the license, and indicate whether you made changes.

## What we do not license

Each run record also stores the **raw response text returned by a third-party language model** (the `raw_response` field, and the `design` object parsed from it).

We did not author that text and we do not claim copyright in it. It is reproduced here as a factual record of what a given model returned for a given prompt, which is the evidence the benchmark rests on. Its use remains subject to the terms of the provider that generated it, and those terms differ between providers — some open-weight model licenses attach conditions to model outputs, including conditions on using outputs to train other models.

**If you intend to reuse the raw responses — particularly as training data — check the terms of the model that produced them.** Each record names its `model_id` and `provider`, so the applicable terms are identifiable per row.

The CC BY 4.0 grant above applies to our scores, metrics, annotations, and the structure and selection of the dataset. It does not and cannot extend to third-party model output.

## Citation

If you use this benchmark data, please cite the repository and state which simulator and score versions the results came from. Every record carries `simulator_version` and `score_version`; results produced by different versions are not comparable and must not be pooled.
