---
title: Generated files
aliases: ["Generated files"]
document_type: reference
status: verified
authority: canonical
verified_evidence_digest: sha256:4cd01763d36c2aa77e11b17f0579af26d4f544adad893fb9dd852316748b14b3
last_edited: 2026-07-27
tags: [tooling]
related_code: ["../../../backend/scripts/export-openapi.sh", "../../../frontend/scripts/generate-types.mjs", "../../../scripts/ci/sync-openapi.sh", "../../../tools/docs/", "../../../scripts/secrets/generate-env-files.sh", "../../../infra/images/"]
related_docs: ["Generated reference documentation", "Scripts catalogue", "Repository map"]
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

| Output family | Generator/source | Policy |
| --- | --- | --- |
| `backend/openapi.yaml` | `backend/scripts/export-openapi.sh` | Committed contract; regenerate and review drift. |
| Studio API/schema artifacts | Studio scripts and `frontend/scripts/generate-types.mjs` | Committed; do not hand-edit. |
| Documentation index, health, and discovery output | `tools/docs/` / `python3 -m docsys` | Generated documentation; regenerate only. |
| Repository tree snapshot | `tools/docs/generate-repository-tree.py` | Generated documentation; regenerate only. |
| Development environment files | `scripts/secrets/generate-env-files.sh` | Machine-local and environment-specific. |
| Packer/CDK build output | image tooling and CDK synthesis | Transient unless intentionally captured as evidence. |

The active documentation tree's generated documentation lives under
`project-knowledge/reference/generated/`; do not manually edit it.

## Related documents

- [[generated-index|Generated reference documentation]]
- [[scripts-catalogue|Scripts catalogue]]
- [[repository-map|Repository map]]
