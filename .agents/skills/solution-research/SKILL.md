---
name: solution-research
description: Research reliable existing approaches before creating or finalizing a new feature specification and before writing feature tests; use a brief check for simple internal changes.
---

# Solution research

Invoke this skill before `$speckit-specify` for a new feature, again before finalizing
its specification if scope changes, and before feature tests. It complements the official
Spec Kit workflow; it never authorizes implementation or bypasses approval of the spec
and plan.

1. State the requested problem and unresolved decisions without adding requirements.
2. Inspect existing project code, contracts, and dependencies.
3. When web access is available, search authoritative sources: official documentation,
   maintained repositories, trusted package registries, and standards.
4. Compare up to three relevant approaches for license, maintenance, version and Python
   compatibility, security, complexity, and integration cost. Verify facts from sources;
   label assumptions and unknowns. A library is preferable when it reliably solves the
   problem, but its existence alone is not a reason to add a dependency.
5. Recommend one approach concisely and explain the tradeoff. Record the problem,
   approaches, source URLs, verified version and license information when available,
   advantages, limitations, recommendation, rationale, and unresolved questions.

Use the feature's official Spec Kit `research.md` artifact when applicable. For simple
or purely internal changes, keep a brief documented research check rather than a long
survey. If web access is unavailable, say exactly what could not be verified. Never
fabricate findings, sources, versions, or licenses.
