---
title: Data knowledge
aliases: ["Data knowledge"]
document_type: overview
status: draft
authority: canonical
verified_against_commit: null
tags: [backend, security]
related_code:
  - "../../../backend/app/db/"
  - "../../../backend/app/schema/orm/"
  - "../../../infra/database/"
related_docs:
  - "Responses and encryption"
  - "Database migrations"
  - "Respondent access and continuity"
  - "Security knowledge"
---

# Data knowledge

This branch owns the persistence boundaries that are material to FlowForm's
current behaviour. The repository uses distinct core and response persistence
models: identity, access, survey structure, and submission metadata belong on
the core side, while response envelopes and encrypted answer values belong on
the response side. Application code coordinates crossings between those stores;
the separate schemas do not make a backend compromise harmless.

```text
                    trusted backend process
                      /                 \
                     v                   v
              Core persistence     Response persistence
              ----------------     --------------------
              identity             opaque locators
              access               encrypted envelopes
              survey structure     encrypted answers
              session metadata

                  no database-level cross-store join
```

The branch also records how schema changes are handled. The checked-in database
assets initialize empty disposable databases, while an incremental migration and
rollback process for retained environments is not established here. Detailed
pages own the cryptographic response boundary and the schema-change workflow.

## Related documents

- [[responses-and-encryption|Responses and encryption]]
- [[database-migrations|Database migrations]]
- [[respondent-access-and-continuity|Respondent access and continuity]]
- [[security-index|Security knowledge]]
