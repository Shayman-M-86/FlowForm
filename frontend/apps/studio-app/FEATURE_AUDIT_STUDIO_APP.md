# Studio App Feature Audit (State-Changing Features Only)

This document inventories **state-changing features** in the Studio app and excludes pure navigation. It also distinguishes between:

- **Implemented in UI state only** (local React state / mock mode)
- **Connected to backend APIs**
- **Visible but not wired yet** (button exists, no handler/mutation)

---

## Scope

- App audited: `frontend/apps/studio-app`
- Focused pages:
  - Projects list and project workspace tabs
  - Survey workspace tabs
- Excluded intentionally:
  - Sidebar/header navigation interactions
  - Theme toggles and view-only UI controls

---

## 1) Projects Page (`/projects`)

### Current functionality

- **Create project** via modal form (`New project`):
  - Validates name/slug in form.
  - Calls `useCreateProject().mutateAsync(...)`.
  - On success: closes modal and navigates into newly created project.
  - **Status:** ✅ Backend-connected in normal mode; mock mutation in design preview mode.

### Missing / not present

- Delete project from projects list is not exposed in UI on this page.
- Edit project metadata from list page is not present.

### Suggested additions

- Add row/card actions: **Rename**, **Duplicate**, **Archive**, **Delete**.
- Add optimistic create feedback + toast with project slug and quick open.
- Add conflict handling UX for slug collisions (inline recovery action).

---

## 2) Project → Surveys Tab (`/projects/:slug/surveys`)

### Current functionality

- Displays survey summaries from mock data.
- `New survey` button is visible.
  - **Status:** ⚠️ Not wired (no mutation/handler).

### Missing / not present

- No survey creation flow/modal.
- No survey-level actions in this list (duplicate/archive/delete/publish).

### Suggested additions

- Implement **Create survey** modal (name, slug, initial status, template).
- Add survey card action menu: **Rename**, **Duplicate**, **Archive**, **Delete**.
- Add status transitions inline for draft/published/archived.

---

## 3) Project → Members Tab (`/projects/:slug/members`)

### Current functionality

- **Invite member** modal flow:
  - Enter email, choose role, submit.
  - Adds invited member to local table state.
  - **Status:** ⚠️ Local state only.
- **Change member role** action:
  - Opens role-change modal, saves updated role in table state.
  - **Status:** ⚠️ Local state only.
- **Remove member** action:
  - Opens confirm modal, removes member from table state.
  - **Status:** ⚠️ Local state only.
- **Create/edit/delete custom role from invite flow**:
  - Nested role editor supports custom role lifecycle in local state.
  - **Status:** ⚠️ Local state only.

### Missing / not present

- No backend persistence for invite/change/remove.
- No invitation lifecycle actions (resend/cancel/revoke).
- No audit trail or attribution per change in this tab.

### Suggested additions

- Wire member operations to backend endpoints:
  - `invite`, `update membership role`, `remove membership`.
- Add **Resend invite**, **Revoke invite**, **Transfer ownership**.
- Add safeguards: cannot remove last owner; role downgrade warnings.

---

## 4) Project → Roles Tab (`/projects/:slug/roles`)

### Current functionality

- Shared `RolesWorkspace` supports:
  - **Add custom role**.
  - **Edit custom role** (name, description, permissions).
  - **Delete custom role**.
  - **Override default role permissions** (stored as local overrides).
  - **Filter roles** (all/default/custom), and paged role matrix view.
  - **Status:** ⚠️ Local state only.

### Missing / not present

- No persistence of custom roles/overrides.
- No role usage/dependency check before delete.

### Suggested additions

- Persist role definitions and default-role override policies via API.
- Add **impact preview** before save/delete:
  - “N members currently assigned this role.”
- Add **clone role** and **reset to default permissions** actions.

---

## 5) Project → Settings Tab (`/projects/:slug/settings`)

### Current functionality

- **Edit project title + URL-safe name** with save/reset logic.
  - Saves only to component local state.
  - **Status:** ⚠️ Local state only.
- **Delete project** confirmation flow:
  - Requires typed confirmation of project title.
  - After confirm, navigates back to projects.
  - **Status:** ⚠️ UI-only (no API delete call from this tab).

### Missing / not present

- No persistence to backend for settings changes.
- Delete does not actually call delete mutation in this tab.

### Suggested additions

- Wire save to `PATCH /projects/:id` and delete to `DELETE /projects/:id`.
- Show irreversible warning summary (surveys, members, responses impacted).
- Add soft-delete with recovery window option.

---

## 6) Survey → Overview Tab (`/projects/:slug/surveys/:surveySlug/overview`)

### Current functionality

- Status and quick-action cards are rendered.
- Buttons like **Publish draft** and **Preview live survey** are visible.
  - **Status:** ⚠️ Not wired.

### Missing / not present

- No publish mutation from this tab.
- No preview launch behavior implemented.

### Suggested additions

- Wire **Publish draft** action to version publish endpoint.
- Add **pre-publish validation** checklist (required questions, rule validity).

---

## 7) Survey → Builder Tab (`/projects/:slug/surveys/:surveySlug/builder`)

### Current functionality

- If draft exists: loads `NodePage` builder in memory router.
- If no draft exists: shows **Create new draft** button.
  - **Status:** ⚠️ Create-new-draft button not wired in this shell.

### Missing / not present

- No create-draft mutation from this tab shell.
- Save/publish wiring depends on builder integration and backend endpoints.

### Suggested additions

- Add explicit **Create draft from published** mutation.
- Add autosave status + unsaved-change guard at studio shell level.

---

## 8) Survey → Versions Tab (`/projects/:slug/surveys/:surveySlug/versions`)

### Current functionality

- Displays versions table and status badges.
- Visible actions by status (draft/published/archived):
  - Edit, Preview, Publish, Delete,
  - View live, Create draft copy, Archive,
  - View, Restore as draft,
  - plus top-level **New draft**.
- **Status:** ⚠️ All actions currently UI-only stubs (`onSelect: () => {}`).

### Missing / not present

- No version lifecycle mutations are currently wired.

### Suggested additions

- Implement full version lifecycle endpoints with optimistic updates:
  - create draft, publish, archive, restore, delete draft.
- Add confirmation modals for destructive transitions.
- Add rules for one-active-draft constraint with clear error messages.

---

## 9) Survey → Members Tab (`/projects/:slug/surveys/:surveySlug/members`)

### Current functionality

- Survey access grid over project members.
- **Change survey role** (override) modal updates local role map.
- **Remove survey role** reverts to inherited project role permissions.
- **Status:** ⚠️ Local state only.
- **Add member** button visible.
  - **Status:** ⚠️ Not wired.

### Missing / not present

- No persistence of survey-role overrides.
- No add-member flow tied to project membership invitation.

### Suggested additions

- Persist survey role overrides via API.
- Add add-member flow that can:
  - invite new project member,
  - or assign existing project member to survey-specific role.
- Add bulk role updates for multiple members.

---

## 10) Survey → Roles Tab (`/projects/:slug/surveys/:surveySlug/roles`)

### Current functionality

- Reuses `RolesWorkspace` for survey-scoped roles.
- Supports add/edit/delete custom survey roles and default-role overrides.
- **Status:** ⚠️ Local state only.

### Suggested additions

- Persist survey role models separately from project roles.
- Show inheritance/precedence between project and survey role systems.

---

## 11) Survey → Links Tab (`/projects/:slug/surveys/:surveySlug/links`)

### Current functionality

- Shows public link cards when survey is published.
- Buttons visible per link:
  - **Copy link**
  - **Disable/Enable**
  - **Regenerate**
- Top-level **Create link** button shown (enabled only when published).
- **Status:** ⚠️ All link actions currently not wired.

### Suggested additions

- Implement endpoints for create/toggle/regenerate/copy tracking.
- Add link constraints:
  - expiry date,
  - max submissions,
  - one-time token,
  - email-bound access.
- Add explicit destructive confirm for regenerate (old token invalidation).

---

## 12) Survey → Settings Tab (`/projects/:slug/surveys/:surveySlug/settings`)

### Current functionality

- Editable fields for name/description/internal notes.
- Toggles:
  - allow anonymous,
  - close after date.
- Buttons visible:
  - **Save changes**,
  - **Archive**,
  - **Delete**.
- **Status:** ⚠️ Controls are UI-only; no persistence mutations are wired.

### Suggested additions

- Wire settings save to survey settings endpoint.
- Wire archive/delete with confirmations and permission checks.
- Add response policy options (edit after submit, multiple submissions, captcha, rate-limit).

---

## 13) Survey → Responses Tab (`/projects/:slug/surveys/:surveySlug/responses`)

### Current functionality

- Read-only summary cards from mock response count.
- Placeholder note for full table/export.
- **Status:** No state-changing features implemented.

### Suggested additions

- Add response management actions:
  - export CSV/JSON,
  - delete submission (permission gated),
  - redact PII fields,
  - reopen partial submissions.

---

## Cross-cutting gaps and highest-value next features

## A) Persistence gap (largest)
Most state-changing actions in Studio are local-state only or stubbed. Highest leverage is wiring these to real mutations with query invalidation and optimistic UI.

## B) Confirmation and guardrails
Add standardized confirmation patterns for:
- delete/archive/publish/regenerate-token actions,
- role changes affecting access,
- ownership transfers.

## C) Auditability
Add “who changed what, when” surfaces and integrate with backend audit log for project/survey/member/role/link mutations.

## D) Permissions enforcement UX
Disable/hide restricted actions based on role claims from backend permissions to prevent ambiguous failures.

## E) Bulk workflows
For admin-heavy use:
- bulk invite,
- bulk role update,
- bulk archive/delete drafts,
- batch link disable/regenerate.

---

## Prioritized implementation shortlist

1. **Wire project settings + delete + members CRUD to backend** (core admin workflows).
2. **Wire survey version lifecycle (create draft/publish/archive/restore/delete)**.
3. **Wire survey public link lifecycle (create/enable-disable/regenerate)**.
4. **Persist project/survey custom roles and role overrides**.
5. **Add audit log entries + confirmations for all destructive actions**.

