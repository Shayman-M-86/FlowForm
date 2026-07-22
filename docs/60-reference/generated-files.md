---
title: Generated files
aliases:
  - "Generated files"
document_type: reference
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [tooling]
related_code:
  - "../../backend/scripts/export-openapi.sh"
  - "../../frontend/scripts/generate-types.mjs"
  - "../../scripts/ci/sync-openapi.sh"
  - "../../scripts/docs/"
  - "../../scripts/secrets/generate-env-files.sh"
  - "../../infra/images/"
related_docs:
  - "Generated documentation"
  - "Scripts catalogue"
  - "Repository map"
---

# Generated files
Provides concise verified reference facts for generated files.

## Reference scope

This page identifies maintained generated or machine-rendered files, their source, and whether they are committed. Generated output must be refreshed through its owner rather than edited as primary source.

## Canonical source

The generator and its scanned inputs are authoritative. A committed output is a reviewable snapshot and CI may check it for drift, but behaviour should be changed at the source model or generator.

## Entries

| Output | Generator or source | Policy |
| --- | --- | --- |
| `backend/openapi.yaml` | `backend/scripts/export-openapi.sh` and backend route/schema registries | Committed; regenerate, lint, and review contract drift. |
| `frontend/apps/studio-app/src/api/generated/schema.ts` | `openapi-typescript` via Studio `openapi:types` / `openapi:generate` | Committed; do not hand-edit. |
| `frontend/apps/studio-app/src/api/generated/rbac.gen.ts` | `frontend/scripts/generate-types.mjs` from `backend/openapi.yaml` | Committed; do not hand-edit. |
| `frontend/packages/schema/src/generated/*.gen.ts` | `frontend/scripts/generate-types.mjs` from builder schemas/extensions in `backend/openapi.yaml` | Committed; do not hand-edit. |
| `docs/90-generated/repository-tree.md` | `scripts/docs/generate-repository-tree.py` | Committed generated documentation. |
| `docs/90-generated/documentation-index.json` | `PYTHONPATH=scripts/docs python3 -m docsys index` | Committed machine-readable documentation index. |
| `docs/90-generated/documentation-dashboard.md`, `documentation-health.json` | `PYTHONPATH=scripts/docs python3 -m docsys health` | Committed health snapshot; do not hand-edit. |
| `infra/images/*/manifests/*.json` | Packer builds and image wrappers | Build output; excluded from normal source review unless intentionally captured as evidence. |
| `infra/env/dev/.backend.env`, `.db.core.env`, `.db.response.env` | `scripts/secrets/generate-env-files.sh` | Machine-local generated development configuration; values are environment-specific and gitignored. |
| `/opt/flowform/backend.env`, `/opt/flowform/proxy.env` | `infra/deployment/bootstrap/bootstrap-app.sh`, `bootstrap-proxy.sh` | Root-owned deployed runtime configuration rendered from scoped SSM paths; treat the files as sensitive because the current proxy path includes a Grafana token. |
| `infra/deployment/aws/cdk/cdk.out/` | AWS CDK synthesis | Transient build output; regenerate from CDK source. |

## Update procedure

Run the owning generator, inspect the diff, and run its drift check where one exists. Update this catalogue when an output or source boundary changes; update files under `docs/90-generated/` only through their generator.

## Related documents

- [[90-generated/README|Generated documentation]]
- [[scripts-catalogue|Scripts catalogue]]
- [[repository-map|Repository map]]
