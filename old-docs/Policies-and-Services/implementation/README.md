# Public Submissions Implementation

Split implementation plan for aligning `backend/app/services/public_submissions`
with the Policies and Services docs.

Use the `caveman` skill for implementation explanations and pass reports unless
the user says otherwise.

## Source of Truth

* `../core-policies.md`
* `../Flows/Public-slug-flow.md`
* `../Flows/General-Link-Flow.md`
* `../Flows/Private-link-access-Flow.md`
* `../Flows/Authenticated-link-access-Flow.md`
* `../Flows/shared/resolve-link-token.md`
* `../Flows/shared/check-recognition-token.md`
* `../Flows/shared/subject-resolution.md`
* `../Flows/shared/logged-in-reconciliation.md`
* `../Flows/shared/issue-or-rotate-recognition-token.md`
* `../Flows/shared/consume-single-use-link.md`

When docs and code disagree, stop and make a local plan. Do not average them.

If a later pass proves an earlier contract wrong, stop and revise it before continuing.
