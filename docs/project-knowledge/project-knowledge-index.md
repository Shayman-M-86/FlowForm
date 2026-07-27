---
title: Project Knowledge
aliases: ["Project Knowledge"]
document_type: overview
status: draft
authority: canonical
verified_evidence_digest: null
tags: [meta]
related_code:
  - "../../backend/app/"
  - "../../frontend/apps/"
  - "../../frontend/packages/"
  - "../../infra/"
related_docs: ["FlowForm documentation", "Development workspace", "Backend knowledge", "Data knowledge", "Security knowledge", "Product knowledge", "Frontend implementation", "Operations knowledge", "Engineering practices", "Infrastructure knowledge", "Reference documentation"]
---

# Project Knowledge

Project Knowledge is the maintained explanation of FlowForm as it currently
exists. It combines product meaning with the software, data, security,
infrastructure, and operational boundaries that realize that meaning. Current
code, tests, schemas, configuration, CI, and infrastructure definitions remain
the source of truth.

## System at a glance

FlowForm is a survey platform for building adaptive questionnaires, publishing
versioned survey content, controlling team access, distributing respondent
links, collecting answers, and reviewing results. Studio users manage projects,
surveys, roles, participants, links, and results through an authenticated web
application and Flask API. Respondents use public or assigned access to complete
a published survey version.

The typical product path is:

```text
create project
  -> create survey and draft version
  -> build questions and rules
  -> publish version
  -> publish public access or issue a link
  -> collect a submission and answers
  -> review or export results
```

That path crosses several independently maintained boundaries. The frontend
owns browser experiences and shared survey UI. The backend owns HTTP contracts,
application rules, and coordination. Core persistence holds application,
authorization, survey, and submission metadata. A separate response store holds
encrypted response material. Infrastructure and operations provide the runtime,
deployment, configuration, and observability surfaces around those components.

```text
Studio user ----------------+
                            |
Respondent --> Browser UI --+--> Backend API --> Core store
                            |         |
Auth0 ----------------------+         +---------> Response store
                                      |
                                      +---------> KMS / secrets / email

Infrastructure runs the components; operations carries their runtime signals.
```

## People, systems, and stores

| Actor or dependency | Role in the system |
| --- | --- |
| Public visitor | Uses the public site for product and documentation content. |
| Studio user | Authenticates through Auth0 and manages projects, surveys, access, participants, and results. |
| Respondent | Opens public or assigned survey access and submits answers against a published version. |
| Backend API | Exposes account, Studio, respondent, and system operations under `/api/v1`. |
| Core PostgreSQL | Stores users, authorization, projects, surveys, versions, subjects, links, and submission metadata. |
| Response PostgreSQL | Stores encrypted response envelopes and answers through opaque application-level linkage. |
| Auth0 | Provides interactive identity and bearer tokens verified by the backend. |
| AWS services | KMS, Secrets Manager, and SES support encryption keys, runtime secrets, and application email where configured. |

This is a logical system context, not evidence that any particular deployment
is live or healthy. Local Compose, shared runtime definitions, Proxmox
rehearsal, and AWS CDK are distinct realizations with different completeness.

## Responsibility model

The collection is organized by ownership rather than by document format.
Product knowledge explains user-visible concepts and rules. Frontend and
backend knowledge explain the application responsibilities that implement
those rules. Data and security knowledge own persistence, encryption,
identity, authorization, and trust boundaries. Infrastructure and operations
explain how the system is assembled, deployed, observed, and maintained.
Engineering practices define cross-cutting ways of working, while reference
material records exact facts that support those explanations.

These areas are not independent silos. A feature may begin with a product rule,
cross frontend and backend responsibilities, persist through the data model,
and depend on security and operational guarantees. Each fact still has one
primary home; related documents connect the full path without repeating the
same explanation at every layer.

## Evidence and maturity

Canonical authority is earned through implementation evidence. A verified page
records the commit it was checked against; a draft exposes incomplete review;
and a scaffold carries no claim beyond its declared boundary. Proposals,
investigations, and unresolved decisions belong in [[development-workspace-index|Development
workspace]] until implementation evidence supports durable knowledge here.

This overview remains draft until its system-level statements are checked
against a committed implementation baseline.

## Where responsibility continues

- [[product-index|Product knowledge]] owns survey-building, respondent-access,
  continuity, and other user-visible rules.
- [[frontend-index|Frontend implementation]] and [[backend-index|Backend
  knowledge]] own browser and API/application responsibilities.
- [[data-index|Data knowledge]] and [[security-index|Security knowledge]] own
  persistence, encryption, identity, authorization, and trust boundaries.
- [[infrastructure-index|Infrastructure knowledge]] and
  [[operations-index|Operations knowledge]] own runtime assembly, deployment,
  configuration, observability, and tracing.
- [[engineering-practices-index|Engineering practices]] owns cross-cutting
  development and delivery workflows.
- [[reference-index|Reference documentation]] provides exact catalogues and
  reproducible repository facts.

## Known boundary questions

- The root README historically assigned respondent form filling to the public
  site, while the checked route tree placed the token respondent page in the
  Studio build. The intended long-term frontend ownership remains to be
  reconciled.
- Repository infrastructure describes several deployment models but does not,
  by itself, establish which topology is currently deployed.

## Related documents

- [[docs-index|FlowForm documentation]]
- [[development-workspace-index|Development workspace]]
- [[backend-index|Backend knowledge]]
- [[data-index|Data knowledge]]
- [[security-index|Security knowledge]]
- [[product-index|Product knowledge]]
- [[frontend-index|Frontend implementation]]
- [[engineering-practices-index|Engineering practices]]
- [[infrastructure-index|Infrastructure knowledge]]
- [[operations-index|Operations knowledge]]
- [[reference-index|Reference documentation]]
