---
title: Links and subjects
aliases: ["Links and subjects"]
document_type: domain
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [backend, security]
related_code:
  - "../../../backend/app/services/survey_links.py"
  - "../../../backend/app/services/participants.py"
  - "../../../backend/app/schema/orm/core/project_subject.py"
  - "../../../backend/app/schema/orm/core/survey_access.py"
  - "../../../frontend/apps/studio-app/src/lib/surveyAccessDesign.ts"
  - "../../../frontend/apps/studio-app/src/pages/SurveyWorkspaceTabPages/SurveyAccessTab.tsx"
change_triggers:
  - "../../../backend/app/services/public_submissions/core/resolution/"
related_docs:
  - "Backend knowledge"
  - "Respondent access and continuity"
  - "Identity and authentication"
  - "Submissions"
  - "Security model"
---

# Links and subjects

This domain implements [[respondent-access-and-continuity|Respondent access and
continuity]]. It separates survey reachability from subject resolution and keeps
both separate from submission persistence. Studio membership and permissions
are outside this boundary.

Access resolution validates publication, response-store availability, survey
visibility, and the current state of a public slug or link. General links are
unassigned and reusable. Private and authenticated links carry a participant
assignment and are single-use; authenticated links additionally require the
logged-in actor to match the participant's linked identity.

```text
slug or link --> AccessResolver --> access grant
                                      |
recognition cookie --> token lookup --+
                                      |
logged-in identity -------------------+
                                      v
                               SubjectResolver
                                      |
                       +--------------+--------------+
                       |                             |
                 subject writes                token action
                       |                             |
                       +--------------+--------------+
                                      v
                               SessionStarter
```

For open access, subject resolution prefers a logged-in project identity, then
a valid project recognition token, then a new anonymous subject. For assigned
access, the assigned participant subject wins. When evidence converges on two
subjects, the weaker record is pointed at the canonical subject and the browser
token can be rotated to preserve future continuity.

Subject resolution returns the final subject and required effects. The
session-start orchestration applies subject aliases, identity attachment, and
recognition-token actions in the core transaction. It then creates the core
session and response envelope and consumes an assigned link as part of the
successful start boundary.

Studio exposes the same three link types enforced by the service. Private
surveys allow participant-specific `private` and `authenticated` links but not
general links. Link updates send only fields the operator changed, so enabling
or disabling a link does not clear its participant assignment. Respondent URLs
use `/respond/{token}` consistently in API responses, Studio, and invitation
email delivery.

Email delivery records `emailed_at` only when the configured email provider
returns a message identifier. Disabled delivery returns no identifier, leaves
the timestamp unchanged, and is shown as not sent in Studio.

The domain does not authorize Studio users or persist answer values. Those
responsibilities belong respectively to [[projects-and-access|Projects and
access]] and [[responses-and-encryption|Responses and encryption]].

## Related documents

- [[backend-index|Backend knowledge]]
- [[respondent-access-and-continuity|Respondent access and continuity]]
- [[submissions|Submissions]]
- [[identity-and-authentication|Identity and authentication]]
