---
title: Documentation generator guide
document_type: overview
status: scaffold
authority: canonical
verified_against_commit: null
related_code: ["scripts/docs/"]
related_docs: ["../README.md", "documentation-model.md"]
---

# Documentation generator guide
Guides agents and scripts that update FlowForm documentation from verified repository evidence.

## Required reading order
Agents must read [docs/README.md](../README.md), then the overview documents, then the target document before writing. TODO: Verify this against the current implementation.

## Evidence rules
Inspect the current implementation before writing, using source code, tests, configuration, CI, and infrastructure definitions as supporting evidence. Treat `old-docs/` only as untrusted historical context and never copy it without re-verifying every claim. TODO: Verify this against the current implementation.

## Claim classification
Distinguish current behaviour, planned behaviour, and assumptions. Report contradictions instead of silently choosing one source. TODO: Verify this against the current implementation.

## Repeatable process
Select a document → Read its purpose and scope → Inspect relevant source code → Inspect tests and configuration → Inspect related runtime or deployment definitions → Write only verified claims → Add implementation references → Link related documents → Record the verified commit → Run documentation validation. TODO: Verify this against the current implementation.

## Reference and navigation discipline
Add exact code references only after verifying them, record the commit SHA used for verification, link concepts to workflows and implementation files, avoid duplicating the same explanation, and update navigation whenever files are added. TODO: Verify this against the current implementation.

## Planning discipline
Keep temporary plans in `70-planning/`, not in canonical architecture documents. Use ADRs only for decisions that remain relevant after implementation. TODO: Verify this against the current implementation.

## Answering repository questions
When answering questions, cite files and terminal commands used, identify whether claims are verified, and explain contradictions or missing evidence. TODO: Verify this against the current implementation.
