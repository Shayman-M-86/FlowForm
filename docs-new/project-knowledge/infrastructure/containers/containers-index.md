---
title: Container runtime documentation
aliases: ["Container runtime documentation"]
document_type: overview
status: verified
authority: canonical
verified_against_commit: 0edae9082dc3381cc1376e8a81276bf5c7bebf88
tags: [infrastructure, backend]
related_code:
  - "../../../../infra/containers/"
related_docs: ["Infrastructure knowledge", "Runtime containers"]
---

# Container runtime documentation

Owns the Compose service boundaries and strategy overlays used by FlowForm.
The definitions support development, test, AWS-oriented, and rehearsal
variants; no page here asserts which variant is currently running.

## Documents in this branch

- [[runtime-containers|Runtime containers]] describes the shared proxy and app
  host contract, development/test variants, and strategy overlays.
