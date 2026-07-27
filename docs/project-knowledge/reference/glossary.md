---
title: Glossary
aliases: ["Glossary"]
document_type: reference
status: draft
authority: canonical
verified_against_commit: null
tags: [backend, frontend, security]
related_code:
  - "../../../backend/app/schema/orm/core/"
  - "../../../backend/app/schema/orm/response/"
  - "../../../backend/app/services/public_submissions/"
  - "../../../frontend/apps/studio-app/"
  - "../../../frontend/apps/public-site/"
related_docs:
  - "Reference documentation"
  - "Projects and access"
  - "Surveys and versioning"
  - "Links and subjects"
  - "Submissions"
---

# Glossary

Shared terms used by the FlowForm documentation. Read each definition with its
owning domain page and implementation evidence.

| Term | Meaning |
| --- | --- |
| Project | Top-level collaboration scope for surveys, memberships, subjects, response-store selection, and permissions. |
| Survey | Project-owned container whose content is held by numbered versions. |
| Survey version | Draft, published, or archived snapshot; an attempt is tied to one exact version. |
| Respondent | Person or browser using the respondent-facing flow; not itself a persisted entity type. |
| Subject | Stable project-scoped record used to provide respondent continuity. |
| Participant | Enrolled subject paired with an identity; not every subject is a participant. |
| Survey link | Bearer access record for a survey, separate from a browser session or recognition token. |
| Submission | Product term for a respondent attempt and collected result; the core model centres on a submission session. |
| Submission session | Core attempt metadata, including lifecycle, selected version, access context, and response-store context. |
| Submission answer slot | Core pointer for one session/question pair; it does not hold the plaintext answer. |
| Response store | Project-scoped destination selection for response payloads. |
| Response envelope | Response-side encrypted container identified through an opaque session locator. |

Studio is the React/Vite application under `frontend/apps/studio-app/`; the
public site is the Astro application under `frontend/apps/public-site/`. The
legacy glossary records that the respondent route has lived with Studio, but
current product ownership must be checked before treating that placement as a
durable guarantee.

## Related documents

- [[reference-index|Reference documentation]]
- [[projects-and-access|Projects and access]]
- [[surveys-and-versioning|Surveys and versioning]]
- [[links-and-subjects|Links and subjects]]
- [[submissions|Submissions]]
