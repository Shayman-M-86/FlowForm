---
title: Generated files
aliases: ["Generated files"]
document_type: reference
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-03
tags: [tooling]
related_code:
  - "../../../backend/scripts/export-openapi.sh"
  - "../../../frontend/scripts/generate-types.mjs"
  - "../../../scripts/ci/sync-openapi.sh"
  - "../../../scripts/secrets/generate-env-files.sh"
change_triggers:
  - "../../../tools/"
  - "../../../infra/machine-images/"
related_docs: ["Generated reference documentation", "Configuration and generated output", "Repository ownership and entry points"]
---

# Generated files

Generated output is refreshed through its owner; a committed snapshot is not
the primary source. Inspect the generator and scanned inputs, then run its
drift check where available.

```text
maintained source + generator
            |
            v
       generated output
            |
      drift / validation check
            |
            +--> commit when repository-owned
            +--> keep local when environment-specific
            +--> discard when transient
```

| Output family | Owning source | Policy |
| --- | --- | --- |
| API contracts and browser artifacts | Backend contract export and frontend generation. | Regenerate and review committed drift. |
| Documentation inventories and health output | Documentation tooling. | Regenerate only. |
| Local configuration material | Local configuration tooling. | Environment-specific; do not treat as canonical. |
| Build and deployment output | The owning image or deployment tool. | Normally transient unless deliberately captured as evidence. |

The active documentation tree's generated documentation lives under
`project-knowledge/reference/generated/`; do not manually edit it.

## Related documents

- [[generated-index|Generated reference documentation]]
- [[configuration-catalogue|Configuration and generated output]]
- [[repository-map|Repository ownership and entry points]]
