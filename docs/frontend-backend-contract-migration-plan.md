# Frontend/Backend Contract Migration Plan

Date: 2026-06-22

## Purpose

This is a planning artifact for bringing the frontend back into alignment with
the recent backend API, schema, OpenAPI, and session-response changes.

The goal is not to manually inspect every frontend file first. The goal is to
use the backend OpenAPI contract and generated frontend types as the primary
diff oracle, then let TypeScript and targeted runtime tests expose the manual
adapter work that remains.

## Current Evidence

- Last commit touching `frontend/`: `9ebe939` on `2026-06-17`, `Add end-to-end tests for submission session flows`.
- Commits since that frontend touch: `31` total.
- Backend-touching commits since then: `22`.
- Frontend-touching commits since then: `0`.
- Backend/docs files changed since that anchor: `192`.
- Key changed backend areas:
  - API route files: `33`.
  - API Pydantic schema files: `27`.
  - Public submission services: `15`.
  - Backend tests/contracts: `46`.
  - OpenAPI export/spec files: `2`.
- Backend OpenAPI export is current after regeneration.
- Studio generated OpenAPI types are stale against `backend/openapi.yaml`.

## Main Contract Drift

The generated type diff is large, but the first-order drift is mostly route
namespace movement:

- Old account/auth paths:
  - `/api/v1/me/...`
  - `/api/v1/auth/...`
- New account paths:
  - `/api/v1/account/...`

- Old Studio project paths:
  - `/api/v1/projects/...`
- New Studio project paths:
  - `/api/v1/studio/projects/...`

- Old public respondent paths:
  - `/api/v1/public/...`
- New respondent paths:
  - `/api/v1/respondent/...`

The generated schema comparison showed all `54` old paths removed and `54` new
paths added. That means the first migration pass should treat this as a
contract namespace migration before treating it as a feature rewrite.

## Known Frontend Touch Points

Non-generated frontend files still containing old API prefixes include:

- `frontend/apps/studio-app/src/api/hooks/me.ts`
- `frontend/apps/studio-app/src/api/hooks/members.ts`
- `frontend/apps/studio-app/src/api/hooks/projects.ts`
- `frontend/apps/studio-app/src/api/hooks/roles.ts`
- `frontend/apps/studio-app/src/api/hooks/survey-roles.ts`
- `frontend/apps/studio-app/src/api/hooks/surveys.ts`
- `frontend/apps/studio-app/src/api/hooks/versions.ts`
- `frontend/apps/studio-app/src/api/hooks/nodes.ts`
- `frontend/apps/studio-app/src/api/hooks/links.ts`
- `frontend/apps/studio-app/src/api/hooks/survey-members.ts`
- `frontend/apps/studio-app/src/api/hooks/permissions/index.ts`
- `frontend/apps/studio-app/src/auth/bootstrap/api.ts`
- `frontend/apps/studio-app/src/pages/SurveyWorkspaceTabPages/SurveyResponsesTab.tsx`
- `frontend/apps/studio-app/tests/api/middleware/permissionMiddleware.test.ts`

Observed old-prefix counts across frontend:

- `/api/v1/projects`: `104`.
- `/api/v1/me`: `25`.
- `/api/v1/public`: `8`.
- `/api/v1/auth`: `2`.

## Generated Artifacts

The existing generation path is:

- `frontend/apps/studio-app/package.json`
  - `openapi:export`
  - `openapi:types`
  - `openapi:generate`
  - `openapi:check`
- `frontend/package.json`
  - `generate:types`

Generated outputs observed:

- `frontend/apps/studio-app/src/api/generated/schema.ts`
- `frontend/apps/studio-app/src/api/generated/rbac.gen.ts`
- `frontend/apps/studio-app/src/routeTree.gen.ts`
- `frontend/packages/schema/src/generated/builder.gen.ts`
- `frontend/packages/schema/src/generated/builder-zod.gen.ts`
- `frontend/packages/schema/src/generated/builder-constraints.gen.ts`
- `frontend/packages/schema/src/generated/constraints.gen.ts`

Important guardrail issue:

- `pnpm run openapi:export --check` works.
- The current `openapi:check` script path using `pnpm run openapi:export -- --check` fails before checking generated types.
- Fix this guardrail before relying on frontend OpenAPI checks.

## Migration Strategy

### Pass 1: Guardrails and Generated Contract

1. Fix the Studio `openapi:check` script so the backend export check actually runs.
2. Confirm `backend/openapi.yaml` is current:
   - `bash backend/scripts/export-openapi.sh --check`
3. Regenerate frontend OpenAPI types:
   - `pnpm --dir frontend/apps/studio-app run openapi:types`
4. Regenerate shared schema artifacts:
   - `pnpm --dir frontend run generate:types`
5. Review generated diffs before manual edits.

Success condition:

- Generated files reflect the current backend contract.
- The OpenAPI check command fails only for real generated drift, not script argument forwarding.

### Pass 2: Mechanical Route Namespace Migration

Update hardcoded API paths in Studio hooks and tests.

Suggested mapping:

- `/api/v1/me/...` -> `/api/v1/account/...`
- `/api/v1/auth/bootstrap-user` -> `/api/v1/account/bootstrap-user`
- `/api/v1/projects/...` -> `/api/v1/studio/projects/...`
- `/api/v1/public/...` -> `/api/v1/respondent/...`

This pass should stay mostly mechanical. Avoid redesigning UI state during this
pass unless TypeScript proves the response/request shape changed at the same
call site.

Success condition:

- API hooks reference paths that exist in the regenerated `schema.ts`.
- Permission middleware tests use current route patterns.

### Pass 3: Schema Shape and Adapter Migration

After path migration, use TypeScript failures as the manual work queue.

Likely areas:

- Submission session request/response models split under:
  - `start`
  - `answers`
  - `events`
  - `completion`
- Answer payload model moved under shared submission-session schema files.
- Admin response schemas changed:
  - `saved_at` no longer appears on admin answer/revision response models.
- Link terminology changed:
  - `PublicLink` operation names moved toward `SurveyAccessLink`.
- Account/auth route groups moved from `me/auth` to `account`.
- Studio project and survey route groups now live under the `studio/projects`
  prefix.

Success condition:

- Studio typecheck errors are resolved by current schema semantics, not by
  widening types or casting away drift.

### Pass 4: Builder and Public Site Boundaries

Handle shared builder/schema package changes separately from Studio API hooks.

Rules:

- Treat `frontend/packages/schema/src/generated/builder-zod.gen.ts` as the
  structural validation source of truth for builder imports.
- Keep backend row shape, builder draft shape, published/public schema shape,
  and runtime answer shape distinct.
- Remember that `@flowform/builder` is shared by Studio and Public Site.

Success condition:

- Builder package validates against regenerated schema artifacts.
- Public Site usage of builder/form-filler code still matches runtime answer
  shapes.

### Pass 5: Verification Ladder

Run checks from smallest to broadest:

1. Backend OpenAPI:
   - `bash backend/scripts/export-openapi.sh --check`
2. Studio OpenAPI/generated checks:
   - fixed `pnpm --dir frontend/apps/studio-app run openapi:check`
3. Studio TypeScript:
   - `frontend/node_modules/.bin/tsc -p frontend/apps/studio-app/tsconfig.json --noEmit`
4. Shared schema/builder validation:
   - `frontend/node_modules/.bin/tsc -p frontend/packages/builder/tsconfig.json --noEmit`
5. Studio tests:
   - `pnpm --dir frontend/apps/studio-app test`
6. Studio build:
   - `pnpm --dir frontend/apps/studio-app build`
7. Public Site build:
   - `pnpm --dir frontend/apps/public-site build`

If a broad check fails due to known unrelated strictness, isolate the failing
area instead of treating the entire migration as blocked.

## Recommended Work Order

1. Fix `openapi:check`.
2. Regenerate OpenAPI/types/schema artifacts.
3. Commit or checkpoint generated-only diffs.
4. Migrate route prefixes in Studio hooks/tests.
5. Run Studio TypeScript and convert errors into a checklist.
6. Fix request/response shape mismatches feature by feature.
7. Validate builder/public-site boundaries.
8. Run the verification ladder.

## Do Not Do First

- Do not manually rewrite every frontend consumer before regenerating types.
- Do not paper over schema drift with broad casts.
- Do not blend Studio API hook migration with builder runtime-shape migration.
- Do not assume generated files are enough; the route namespace changes require
  manual hook updates.
