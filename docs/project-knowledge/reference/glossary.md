---
title: Glossary
aliases: ["Glossary"]
document_type: reference
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [backend, frontend, security]
related_code: []
change_triggers:
  - "../../../backend/app/schema/orm/core/"
  - "../../../backend/app/schema/orm/response/"
  - "../../../backend/app/services/public_submissions/"
  - "../../../frontend/apps/studio-app/"
  - "../../../frontend/apps/public-site/"
related_docs:
  - "Reference documentation"
  - "Projects and access"
  - "Surveys and versioning"
  - "Respondent access and continuity"
  - "Links and subjects"
  - "Submissions"
  - "Responses and encryption"
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
| Canonical subject | Subject selected as the durable identity when two subject observations are reconciled. |
| Participant | Enrolled subject paired with an identity; not every subject is a participant. |
| Survey link | Bearer access record for a survey, separate from a browser session or recognition token. |
| General link | Reusable, unassigned survey link for public or link-only access. |
| Private link | Single-use survey link assigned to a participant without requiring login. |
| Authenticated link | Single-use assigned link whose participant identity must match the logged-in user. |
| Recognition token | Project-scoped browser credential used as subject-continuity evidence; it grants no survey access by itself. |
| Browser resume token | Credential for resuming one submission session; only its hash is stored in core data. |
| Submission | Product term for a respondent attempt and collected result; the core model centres on a submission session. |
| Submission session | Core attempt metadata, including lifecycle, selected version, access context, and response-store context. |
| Submission answer slot | Core pointer for one session/question pair; it does not hold the plaintext answer. |
| Response store | Project-scoped destination selection for response payloads. |
| Response envelope | Response-side encrypted container identified through an opaque session locator. |
| Session locator | Opaque response-side identifier derived from a core session ID and versioned linkage key. |
| Answer locator | Opaque response-side identifier derived from a core answer-slot ID and versioned linkage key. |
| Survey branch key | Per-survey key wrapped by KMS and used to wrap session data-encryption keys. |
| Session data-encryption key | Per-session key that encrypts current answer payloads. |

Studio is the React/Vite application under `frontend/apps/studio-app/`; the
public site is the Astro application under `frontend/apps/public-site/`. The
respondent route is currently implemented in Studio, but that location is an
implementation choice rather than a product guarantee.

## Related documents

- [[reference-index|Reference documentation]]
- [[projects-and-access|Projects and access]]
- [[surveys-and-versioning|Surveys and versioning]]
- [[respondent-access-and-continuity|Respondent access and continuity]]
- [[links-and-subjects|Links and subjects]]
- [[submissions|Submissions]]
- [[responses-and-encryption|Responses and encryption]]
