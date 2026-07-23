---
title: Generated documentation
aliases:
  - "Generated documentation"
document_type: generated-index
status: scaffold
authority: canonical
verified_against_commit: null
tags: [meta]
related_code:
  - "../../scripts/docs/"
related_docs:
  - "Documentation generator guide"
  - "Generated files"
  - "Repository tree snapshot"
  - "API routes"
  - "CI workflows"
  - "Configuration index"
  - "Dependency map"
  - "Infrastructure resources"
  - "Documentation health dashboard"
---

# Generated documentation
Indexes documentation intended to be reproducible from repository contents.

## Generated-file policy
Generated files must identify the generator, scanned sources, and no-manual-edit expectations. TODO: Verify this against the current implementation.

## Available generated documents
This directory includes repository tree, dependency map, API routes, CI workflows, infrastructure resources, and configuration index scaffolds, plus the reproducible [[documentation-dashboard|health dashboard]]. The machine-readable `documentation-index.json` and `documentation-health.json` are also generated here for tooling and agents. TODO: Verify the scaffolds against the current implementation.

## Generator scripts
Generator and validation scripts live under `scripts/docs/`. The `docsys` package (`scripts/docs/docsys/`) builds the documentation index, health dashboard, and impact/freshness reports. TODO: Verify this against the current implementation.

## Regeneration workflow
Run the relevant generator, review diffs, validate metadata and links, then record the verified commit. TODO: Verify this against the current implementation.

## Manual edit exception
Manual edits are allowed only to improve scaffold rules until generation is fully implemented. TODO: Verify this against the current implementation.

## Related documents

- [[documentation-generator-guide|Documentation generator guide]]
- [[generated-files|Generated files]]
- [[90-generated/repository-tree|Repository tree snapshot]]
- [[api-routes|API routes]]
- [[ci-workflows|CI workflows]]
- [[configuration-index|Configuration index]]
- [[dependency-map|Dependency map]]
- [[infrastructure-resources|Infrastructure resources]]
- [[documentation-dashboard|Documentation health dashboard]]
