---
title: System context
aliases: ["System context", "System summary"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-04
tags: [backend, frontend, infrastructure, security]
related_code:
  - "../../frontend/apps/public-site/src/pages/index.astro"
  - "../../frontend/apps/studio-app/src/routeTree.gen.ts"
  - "../../backend/app/api/v1/__init__.py"
  - "../../backend/app/db/manager.py"
change_triggers:
  - "../../frontend/apps/"
  - "../../backend/app/api/v1/"
  - "../../backend/app/aws/"
  - "../../infra/"
related_docs:
  - "Project Knowledge"
  - "Product knowledge"
  - "Component map"
  - "Identity and authentication"
  - "Responses and encryption"
  - "Deployment architecture"
---

# System context

FlowForm is a survey platform for authoring and publishing versioned survey
content, controlling operator and respondent access, collecting encrypted
answers, and reviewing results. This page identifies the people, software
surfaces, persistent stores, and external systems around that lifecycle. It is
a logical context rather than a deployed-network or environment-health claim.

## People and entry points

| Actor | Current interaction |
| --- | --- |
| Public visitor | Uses the Astro Public Site for product and documentation content. |
| Studio user | Uses the React Studio application and authenticated API to manage projects, surveys, access, participants, and results. |
| Respondent | Uses the respondent routes currently built into Studio. Public-slug and general-link access may be anonymous; authenticated links also require a matching account identity. |

The Studio route tree owns both `/respond/{token}` and `/s/{slug}`. The Public
Site and Studio are separate builds that reuse frontend workspace packages;
they are not two routes through one deployed application.

## System boundary

```text
public visitor ------------------------> Public Site

Studio user ----+                       Studio application
respondent -----+------------------------------|
                                               | HTTP API
                                               v
Auth0 <---------------------------------> Backend API
                                          /         \
                                         v           v
                                  Core PostgreSQL   Response PostgreSQL
                                         |           |
                                         +-----+-----+
                                               |
                                    AWS key, secret, and email services
```

The backend registers account, Studio, respondent, and system API areas. It
opens separate core and response database engines and sessions. Core storage
owns identity, authorization, survey, access, and submission metadata, while
response storage owns encrypted response envelopes and answer values. Work
crossing those stores is therefore explicitly coordinated by the application.

Auth0 establishes operator and authenticated-respondent identity. Configured
AWS services support key management, versioned secret material, email, and
deployment responsibilities. These dependencies have narrower contracts in
the security, data, and infrastructure branches; their presence in the checkout
does not prove that a live environment is configured or healthy.

## Product lifecycle

```text
project and access
        |
        v
survey draft --> questions and rules --> published version
                                              |
                                      slug or survey link
                                              |
                                              v
                                      submission session
                                              |
                                      encrypted answers
                                              |
                                              v
                                         result review
```

This is an orientation path. Permissions, publication invariants, respondent
continuity, encryption, cross-store failure handling, and deployment operations
remain owned by their linked domain pages.

## Related documents

- [[project-knowledge-index|Project Knowledge]]
- [[product-index|Product knowledge]]
- [[component-map|Component map]]
- [[identity-and-authentication|Identity and authentication]]
- [[responses-and-encryption|Responses and encryption]]
- [[deployment-index|Deployment architecture]]
