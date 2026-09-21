# Architecture Decisions

This file records why specific packages and approaches were chosen, so the reasoning is not lost later.

## ADR-01: Extracting JSON from LLM output (parsing and repair)
**Date:** 2026-06-14

**Context:** Large language models, especially small ones (7B–8B parameters), occasionally produce broken JSON no matter how strictly they are prompted: missing commas, extra braces, markdown code-fence tags and so on.

**Decision:** Use the `json-repair` library instead of writing our own regex-based extraction.

**Reasons:**
1. It is ready-made, tested, and handles hundreds of edge cases.
2. Simple regex solutions can break on complex nested objects.
3. The project's focus is engineering simulation and evaluation; relying on an established open-source tool is more efficient than spending time on a custom JSON parser.

**Note:** Enforcing the JSON format at generation time (constrained decoding) with libraries such as `outlines`, `vllm` or `guidance` remains a possible future move. For now, post-generation repair is the chosen strategy.
