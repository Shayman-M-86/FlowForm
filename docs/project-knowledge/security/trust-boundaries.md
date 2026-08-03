---
title: Trust boundaries
aliases: ["Trust boundaries"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-04
tags: [backend, infrastructure, security]
related_code:
  - "../../../backend/app/core/extensions.py"
  - "../../../infra/containers/images/caddy/rate-limits.caddy"
change_triggers:
  - "../../../backend/app/middleware/auth/"
  - "../../../backend/app/services/public_submissions/"
  - "../../../backend/app/db/"
  - "../../../backend/app/crypto/"
  - "../../../infra/containers/"
  - "../../../infra/deployment/"
related_docs:
  - "Security knowledge"
  - "Security model"
  - "Identity and authentication"
  - "Responses and encryption"
  - "Runtime infrastructure security"
---

# Trust boundaries

A trust boundary is a crossing where a receiver must validate or constrain
data, identity, authority, or network access. It does not make the components
on either side independently secure. FlowForm's important crossings are the
browser and external identity provider, proxy and backend, backend and its two
data stores, backend and AWS key/secret services, and operator or respondent
requests into local access policy.

```text
[Browser] --credentials/input--> [Proxy] --normalized request--> [Backend]
                                                                  |
                           +------------------+--------------------+----------+
                           |                  |                               |
                           v                  v                               v
                     [Core store]      [Response store]             [KMS / secrets]
                     identity/data      encrypted data                 key material

Every arrow is a validation, authorization, or confidentiality boundary.
```

## Request and identity boundaries

Authenticated requests bring an Auth0 credential to backend middleware, which
maps a verified external subject to a local user before project or survey policy
is applied. Public submissions use separate survey and link-resolution rules;
respondent cookies and survey-link credentials are not operator credentials.
At the public boundary, Caddy can reject requests that exceed its per-peer API
or endpoint budgets before they reach Flask; the backend still applies its own
request and business-action limits. The browser-to-API boundary depends on
configured origins, cookie behaviour, client-address attribution, and the
deployed proxy topology, so it should not be summarized as a complete
browser-security guarantee.

## Data and key boundaries

The core store holds identity, access, survey, and session metadata. The
response store holds encrypted envelopes and answers addressed by opaque
locators rather than direct core identifiers. This cryptographic linkage
boundary uses separately managed linkage material to connect the stores. The
backend crosses it to coordinate writes, reads, deletion, and decryption. It
also calls the configured KMS and secrets services for cryptographic operations
and linkage material. Therefore the split limits a database-only disclosure but
does not remove backend, key-service, host, or runtime-memory trust.

## Runtime and deployment boundaries

The repository's deployment and container assets describe a reverse proxy in
front of an application role, private application connectivity, and constrained
container processes. The actual trust decision includes security groups,
forwarded client-address handling, proxy header normalisation, secret delivery,
and host administration. The current Caddy limit key is its direct peer; putting
a CDN or load balancer in front requires an explicit trusted-proxy policy before
forwarded addresses can safely become rate-limit identities. Development and
test Compose topologies can expose different boundaries from the declared cloud
shape.

Host administration, telemetry collection, container control interfaces, and
certificate automation are privileged crossings rather than background
implementation details. [[runtime-infrastructure-security|Runtime
infrastructure security]] describes the invariants used to assess them.

## Review questions

Remaining evidence should establish the trusted-proxy policy, browser origin and
CSRF policy, privileged-user governance, KMS/IAM and secret rotation behaviour,
cross-store failure recovery, multi-instance rate-limit policy, and what
deployment validation proves about the defined network and runtime controls.

## Related documents

- [[security-index|Security knowledge]]
- [[security-model|Security model]]
- [[identity-and-authentication|Identity and authentication]]
- [[responses-and-encryption|Responses and encryption]]
- [[runtime-infrastructure-security|Runtime infrastructure security]]
