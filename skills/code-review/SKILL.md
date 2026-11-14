---
name: code-review
description: Review software changes for correctness, security, regression risk and evidence-backed release readiness.
---
# Code Review

Identify the requested change, baseline behavior, affected call paths, contracts, dependencies and expected invariants. Inspect changed code and relevant callers before recommending acceptance. Check security boundaries, input validation, concurrency, error handling, deterministic calculations, backwards compatibility, tests and release artifacts. Prefer minimal changes that preserve working behavior. Reproduce defects with the smallest safe test; distinguish tests actually run from proposed tests. Report findings by severity with exact location, impact, reproduction evidence and smallest corrective action. Do not approve a change based solely on passing smoke tests or claimed test counts. Treat merge/deployment as separate authorization decisions.
