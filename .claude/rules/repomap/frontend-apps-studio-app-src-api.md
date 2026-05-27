---
paths: frontend/apps/studio-app/src/api/**
---

# frontend/apps/studio-app/src/api/

_Last updated: 2026-05-27 by /repomap_

Centralises all backend communication for the Studio app. The top-level `client.ts` defines `ApiRequestError` (wrapping HTTP status + typed `ApiError`), while `errors.ts` provides helpers (`getErrorMessage`, `getInviteErrorMessage`) that translate backend `ErrorResponse` codes into user-facing strings. Resource modules are grouped under `auth/`, `me/`, `project/` (sub-directories: `projects/`, `surveys/`, `members/`, `permissions/`, `roles/`, `requests.ts`), and `survey/` (sub-directories: `links/`, `members/`, `roles/`, `versions/`), each exposing a `hooks.ts` with React Query wrappers and a `requests.ts` with raw fetch calls. A `generated/` directory holds OpenAPI-derived schema types consumed throughout.
