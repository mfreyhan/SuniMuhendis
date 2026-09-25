# Security policy

## Supported versions

SuniMuhendis is alpha research software. Security fixes are applied to the
latest release line and `main`; older environment tags remain available for
reproducibility but do not receive routine fixes.

## Report a vulnerability

Do not open a public issue for a suspected vulnerability, leaked credential, or
unsafe third-party artifact. Use GitHub's private vulnerability reporting:

https://github.com/suni-muhendis/sm-bench/security/advisories/new

Include the affected version or commit, reproduction steps, expected impact,
and any proposed mitigation. Remove API keys, personal data, and unrelated logs
from the report.

## Research inputs

Benchmark responses and simulator inputs are untrusted data. Production-facing
integrations should apply resource limits and must not execute model-generated
code.
