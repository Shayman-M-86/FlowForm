---
title: Scripts catalogue
aliases: ["Scripts catalogue"]
document_type: reference
status: verified
authority: canonical
verified_evidence_digest: sha256:ef47b7ab1934c1fed9284a6f670c3d6f951f8af4a96621031e9416bc154102cb
last_edited: 2026-07-27
tags: [tooling]
related_code: ["../../../scripts/", "../../../backend/scripts/", "../../../frontend/scripts/", "../../../infra/", "../../../tools/mcp/", "../../../.githooks/"]
related_docs: ["Commands", "Generated files", "Scripts implementation"]
---

# Scripts catalogue

This catalogue groups maintained repository entry points without duplicating
their operational instructions. Script files own shell, Python, and Node helper
behaviour; each `package.json` owns its package aliases. Executable mode alone
does not determine inclusion.

| Area | Maintained locations | Responsibility |
| --- | --- | --- |
| CI contracts | `scripts/ci/` | OpenAPI drift checks and contract generation. |
| Local development | `scripts/dev/` | Bootstrap, hook install, and mock-data loading. |
| Documentation | `tools/docs/` | Documentation generation and validation. |
| Local configuration | `scripts/secrets/` | Development/test configuration preparation. |
| Backend | `backend/scripts/` | Test runner, OpenAPI export, health, integrity, and security helpers. |
| Frontend | `frontend/scripts/` | Frontend contract artifact generation. |
| Infrastructure | `infra/database/`, `infra/deployment/`, `infra/images/`, `infra/tests/` | Database initialization, bootstrap, image, and rehearsal/deployment helpers. |
| Tooling/hooks | `.githooks/`, `tools/mcp/`, `.claude/workflows/` | Repository hook, MCP, and workflow helpers. |

Read an entry point's header or help before invoking it. In particular, image,
deployment, secret, and database helpers may require credentials, external
services, or mutate local/remote state.

## Related documents

- [[commands|Commands]]
- [[generated-files|Generated files]]
- [[scripts-implementation|Scripts implementation]]
