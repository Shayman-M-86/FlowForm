---
title: Repository tree
document_type: reference
status: scaffold
authority: canonical
verified_against_commit: ac7d021ad3716a68638759df684b9a3c32bb4389
related_code:
  [
    "../../backend/",
    "../../frontend/",
    "../../infra/",
    "../../scripts/",
    "../../tools/mcp/",
    "../../.github/workflows/",
  ]
related_docs:
  [
    "../00-overview/repository-map.md",
    "scripts-catalogue.md",
    "configuration-catalogue.md",
    "generated-files.md",
    "../90-generated/repository-tree.md",
  ]
---

# Repository tree

Provides a compact, verified structural reference for the major areas in the current checkout.

## Reference scope

This is a curated tree of major applications, packages, infrastructure, automation, tests, and entry points. Dependency directories, caches, editor state, and exhaustive file listings are intentionally omitted.

## Tree

```text
FlowForm/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── domain/
│   │   ├── repositories/
│   │   ├── schema/
│   │   └── services/
│   ├── scripts/
│   ├── tests/
│   │   ├── e2e/
│   │   ├── integration/
│   │   └── unit/
│   ├── openapi.yaml
│   ├── pyproject.toml
│   └── wsgi.py
├── docs/
│   ├── 00-overview/
│   ├── 10-architecture/
│   ├── 20-domains/
│   ├── 30-workflows/
│   ├── 40-implementation/
│   ├── 50-decisions/
│   ├── 60-reference/
│   ├── 70-planning/
│   └── 90-generated/
├── frontend/
│   ├── apps/
│   │   ├── public-site/
│   │   └── studio-app/
│   │       └── tests/
│   ├── packages/
│   │   ├── builder/
│   │   ├── schema/
│   │   ├── site-shell/
│   │   ├── styles/
│   │   └── ui/
│   ├── scripts/
│   ├── package.json
│   └── pnpm-workspace.yaml
├── infra/
│   ├── cdk/
│   │   ├── flowform_infra/
│   │   └── tests/
│   ├── docker/
│   ├── environments/
│   ├── images/
│   ├── postgres/
│   ├── proxmox/
│   ├── rehearsal/
│   ├── runtime/
│   ├── scripts/
│   └── tests/
├── scripts/
│   ├── ci/
│   ├── dev/
│   ├── docs/
│   ├── secrets/
│   └── tools/
└── tools/
    └── mcp/
```

## Primary entry points

| Surface                   | Entry point                                                                                                                    |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Backend application       | `backend/wsgi.py`, which imports `create_app` from `backend/app/`; the factory is implemented in `backend/app/core/factory.py` |
| Public site               | Astro pages under `frontend/apps/public-site/src/pages/`, configured by `frontend/apps/public-site/astro.config.mjs`           |
| Studio application        | `frontend/apps/studio-app/src/main.tsx` and `frontend/apps/studio-app/src/lib/router.ts`                                       |
| AWS infrastructure        | `infra/cdk/app.py`                                                                                                             |
| Local and test containers | `infra/docker/docker-compose.dev.yml` and `infra/docker/docker-compose.test.yml`                                               |
| Host runtime definitions  | `infra/runtime/compose/` and `infra/runtime/bootstrap/`                                                                        |
| Continuous integration    | `.github/workflows/ci.yml`                                                                                                     |
| Frontend deployment       | `.github/workflows/deploy.yml`                                                                                                 |
| Development MCP server    | `tools/mcp/flowform_dev.py`                                                                                                    |

## Canonical evidence

The implementation tree was derived from tracked paths at the verification commit; the in-progress layered documentation tree was inspected from the preserved working tree. Verification used:

```sh
git rev-parse HEAD
git ls-tree --name-only HEAD
git ls-tree -r --name-only HEAD backend frontend infra scripts tools .github
find backend/app -maxdepth 2 -type d
find frontend/apps frontend/packages -maxdepth 3 -type d
find infra -maxdepth 3 -type d
find backend/tests infra/cdk/tests infra/tests frontend/apps/studio-app/tests -type f
```

The `find` results were filtered to exclude dependency directories, virtual environments, caches, generated build directories, and `old-docs/`. Package manifests, application entry points, test configuration, infrastructure entry points, and workflow files were then inspected directly.

## Update procedure

1. Record the current commit with `git rev-parse HEAD`.
2. Refresh tracked paths with `git ls-tree`; inspect new or removed manifests, entry points, test roots, infrastructure areas, and workflows.
3. Keep this reference curated. Do not add dependency directories, caches, build products, or exhaustive internal module listings.
4. Update the [repository map](../00-overview/repository-map.md) if a major area or reader navigation boundary changes.
5. Regenerate [the generated repository tree](../90-generated/repository-tree.md) only through `scripts/docs/generate-repository-tree.py`; do not paste its exhaustive output into this reference.
6. Update `verified_against_commit`, then run:

```sh
python3 scripts/docs/validate-doc-links.py
python3 scripts/docs/validate-doc-metadata.py
```

## Verification notes

Implementation structure was verified at commit `ac7d021ad3716a68638759df684b9a3c32bb4389`. The layered `docs/` structure and `scripts/docs/` tooling referenced above are current uncommitted Stage 1 working-tree work, so they are not present in that commit.
