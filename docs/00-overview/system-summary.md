---
title: System summary
aliases:
  - "System summary"
document_type: overview
status: verified
authority: canonical
verified_against_commit: ed0fb65df856e18807ee243b4bca512a8d0442b0
tags: [backend, frontend, infrastructure, security]
related_code:
  - "../../backend/app/"
  - "../../frontend/apps/"
  - "../../frontend/packages/"
  - "../../infra/"
related_docs:
  - "FlowForm documentation home"
  - "Glossary"
  - "Repository map"
  - "System context"
  - "Component map"
  - "Projects and access"
  - "Surveys and versioning"
  - "Builder and rules"
  - "Links and subjects"
  - "Submissions"
  - "Responses and encryption"
---

# System summary

FlowForm is a survey platform for building adaptive questionnaires, publishing versioned survey content, controlling team access, distributing response links, collecting answers, and reviewing results.

## Product shape

Authorized Studio users organise surveys within projects and manage access through project- and survey-scoped roles. Survey content is edited as a draft version, published for respondent use, and exposed through a public slug or access link. Those responsibilities are divided among [[projects-and-access|Projects and access]], [[surveys-and-versioning|Surveys and versioning]], [[builder-and-rules|Builder and rules]], and [[links-and-subjects|Links and subjects]].

Respondents resolve a public slug or link token, start a submission session, save answers against the published survey version, and complete that session. Authorized Studio users can then inspect or export results. The lifecycle and privacy-sensitive storage boundary belong to [[submissions|Submissions]] and [[responses-and-encryption|Responses and encryption]].

## Major software surfaces

| Surface | Broad responsibility |
| --- | --- |
| Public site | Astro application for public product and documentation pages, including an in-browser builder demonstration. |
| Studio | React application for authorized project and survey administration; it also hosts the current respondent experience. |
| Shared frontend packages | Survey builder and form-filler behaviour, schemas, UI components, styles, and shared site-shell code used across the frontend workspace. |
| Backend API | Flask application exposing account, Studio, respondent, and system endpoints under `/api/v1`; services enforce application rules and coordinate persistence. |
| Persistence | A core PostgreSQL model holds application, access, survey, and submission metadata, while a separate response model holds encrypted response envelopes and answer ciphertext. |
| Infrastructure and automation | Repository definitions cover local containers, database initialization, shared runtime hosts, machine images, Proxmox rehearsal, AWS CDK, CI, and deployment tooling. |

The external actors, runtime relationships, and deployment boundaries are described by [[system-context|System context]] and [[component-map|Component map]]. The [[repository-map|Repository map]] directs readers from these surfaces to their current entry points.

## Typical lifecycle

```text
Create a project
  -> create a survey and draft version
  -> build questions and rules
  -> publish a version
  -> publish public access or issue an access link
  -> collect a submission session and answers
  -> review or export results
```

This is an orientation path, not a complete workflow contract. Permission checks, version transitions, respondent identity modes, encryption, failure handling, and deployment procedures belong in the linked domain, architecture, and workflow documents.

## Current knowledge boundaries

This summary was checked against the application source, frontend manifests and routes, ORM models, infrastructure tree, and repository automation at commit `ed0fb65df856e18807ee243b4bca512a8d0442b0`. Static repository evidence establishes implemented code and declared infrastructure, but does not prove which environment is currently deployed or healthy.

The root `README.md` says that public form filling is embedded in the Astro public site. The current route tree instead places `/respond/$token` and `RespondPage` in the Studio application, while the public site has only product and documentation routes. This summary follows the current source; the intended long-term ownership of that respondent route remains unresolved documentation drift.

## Open questions

- Which checked-in deployment model, if any, exactly matches the currently running production environment?
- Is respondent form filling intended to remain in the Studio build or move to the public site described by the root README?

## Related documents

- [[README|FlowForm documentation home]]
- [[glossary|Glossary]]
- [[repository-map|Repository map]]
- [[system-context|System context]]
- [[component-map|Component map]]
- [[projects-and-access|Projects and access]]
- [[surveys-and-versioning|Surveys and versioning]]
- [[builder-and-rules|Builder and rules]]
- [[links-and-subjects|Links and subjects]]
- [[submissions|Submissions]]
- [[responses-and-encryption|Responses and encryption]]
