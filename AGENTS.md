# FlowForm agent instructions
Purpose: Defines repository-wide rules for future agents working in FlowForm.

## Metadata
- document_type: agent-instructions
- status: scaffold
- authority: canonical
- verified_against_commit: null
- related_docs: docs/README.md, docs/00-overview/documentation-generator-guide.md

## Core rule
The implementation is the source of truth. Documentation may be incomplete, historical, or wrong until verified against source code, tests, configuration, CI, and infrastructure definitions.
TODO: Verify this against the current implementation.

## Documentation rules
Read `docs/README.md` and `docs/00-overview/documentation-generator-guide.md` before updating documentation. Keep canonical, planning, reference, and generated documents separate.
TODO: Verify this against the current implementation.

## Historical documentation warning
Treat `old-docs/` as untrusted historical context. Do not copy claims from it unless every claim is re-verified against the current implementation.
TODO: Verify this against the current implementation.

## Correct behavior examples
Correct: inspect code before updating a domain document, cite verified paths, record the commit SHA, and update navigation. Correct: place temporary plans under `docs/70-planning/` instead of architecture docs.
TODO: Verify this against the current implementation.

## Incorrect behavior examples
Incorrect: invent ports, commands, architecture guarantees, or security behavior from memory. Incorrect: treat a plan as an accepted decision. Incorrect: leave scaffold files empty or title-only.
TODO: Verify this against the current implementation.

## Pull request expectations
Summaries should state what changed, what was validated, and whether any documentation remains scaffold-only. Documentation-only changes still require link and metadata validation when available.
TODO: Verify this against the current implementation.
