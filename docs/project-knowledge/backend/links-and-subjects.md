---
title: Links and subjects
aliases: ["Links and subjects"]
document_type: domain
status: draft
authority: canonical
verified_against_commit: null
tags: [backend, security]
related_code:
  - "../../../backend/app/services/survey_links.py"
  - "../../../backend/app/services/participants.py"
  - "../../../backend/app/services/public_submissions/core/resolution/"
  - "../../../backend/app/schema/orm/core/project_subject.py"
  - "../../../backend/app/schema/orm/core/survey_access.py"
related_docs:
  - "Backend knowledge"
  - "Identity and authentication"
  - "Submissions"
  - "Security model"
---

# Links and subjects

This draft owns respondent entry credentials and project-scoped pseudonymous
subjects. It separates a survey link or browser-recognition credential from the
subject record that gives a respondent continuity across attempts. Studio
identity and membership are outside this domain.

The legacy model distinguishes general, private, and authenticated survey links;
participants associate an enrolled subject with an identity; and a recognition
token lets a returning browser resolve a subject. Access resolution combines
link state, expiry, assignment, authentication, and subject evidence before a
submission session is created. The source paths above are the evidence boundary
for re-verification of these details.

The domain selects access and subject context. It does not authorize Studio
users, create encrypted envelopes, or persist answers. Those responsibilities
belong respectively to [[identity-and-authentication|Identity and authentication]],
[[projects-and-access|Projects and access]], and [[submissions|Submissions]].

## Related documents

- [[backend-index|Backend knowledge]]
- [[submissions|Submissions]]
- [[identity-and-authentication|Identity and authentication]]
