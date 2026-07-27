---
title: Submissions
aliases: ["Submissions"]
document_type: domain
status: verified
authority: canonical
verified_evidence_digest: sha256:b5c0528d921b131c22eb45ae84ee05a6feaf61d1016992a02d645a03a5071855
last_edited: 2026-07-27
tags: [backend]
related_code:
  - "../../../backend/app/services/public_submissions/"
  - "../../../backend/app/schema/orm/core/submission_session.py"
  - "../../../backend/app/schema/orm/core/submission_answer_slot.py"
  - "../../../backend/app/api/v1/respondent/submission_sessions.py"
  - "../../../backend/tests/e2e/test_submission_session_flows.py"
  - "../../../frontend/apps/studio-app/src/pages/RespondPage.tsx"
related_docs:
  - "Backend knowledge"
  - "Respondent access and continuity"
  - "Links and subjects"
  - "Surveys and versioning"
  - "Responses and encryption"
  - "Data flows"
---

# Submissions

This draft describes one respondent attempt against an exact survey version.
The submission session is the core metadata aggregate: it records lifecycle,
version, subject/access context, and answer slots while response-side data holds
encrypted values. A browser-held resume credential is resolved through its
stored hash rather than stored as a raw core value.

The lifecycle starts only after respondent access and subject resolution. Later
commands load the session, validate its current eligibility, and coordinate
answer save, events, or completion. The legacy model treats answer slots as
core pointers and response answers as encrypted data in a separate store.
Reconciliation handles a subset of partial cross-store failures by examining
in-progress sessions and envelope presence.

On respondent page load, the browser presents its resume cookie with the
current link token or public slug. A matching in-progress session returns its
pinned survey and version before the entry credential is resolved again. This
prevents a consumed single-use link from blocking continuity and prevents a
cookie from one survey being resumed on another survey's URL.

```text
resolve access + subject
          |
          v
create session + response envelope
          |
          v
      in progress
       /   |    \
      v    v     v
 answer  event  resume
      \    |     /
       \   |    /
        complete ------> completed
           |
     partial failure
           v
      reconciliation --> recover / abandon
```

The boundary does not define survey content or Studio results authorization.
See [[surveys-and-versioning|Surveys and versioning]],
[[respondent-access-and-continuity|Respondent access and continuity]],
[[links-and-subjects|Links and subjects]], and
[[responses-and-encryption|Responses and encryption]].

## Related documents

- [[backend-index|Backend knowledge]]
- [[data-flows|Data flows]]
- [[respondent-access-and-continuity|Respondent access and continuity]]
- [[links-and-subjects|Links and subjects]]
- [[surveys-and-versioning|Surveys and versioning]]
