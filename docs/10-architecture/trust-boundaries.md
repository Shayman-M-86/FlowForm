---
title: Trust boundaries
document_type: architecture
status: draft
authority: canonical
verified_against_commit: ed0fb65df856e18807ee243b4bca512a8d0442b0
tags: [backend, infrastructure, security]
related_code:
  - "../../backend/app/core/extensions.py"
  - "../../backend/app/middleware/auth/"
  - "../../backend/app/services/public_submissions/"
  - "../../backend/app/db/"
  - "../../backend/app/crypto/"
  - "../../infra/runtime/compose/"
  - "../../infra/runtime/config/"
  - "../../infra/runtime/bootstrap/"
  - "../../infra/platforms/aws/cdk/flowform_infra/stacks/"
related_docs:
  - "Security model"
  - "System context"
  - "Data flows"
  - "Deployment model"
  - "Runtime containers"
  - "Identity and authentication"
  - "Responses and encryption"
  - "Secrets and configuration"
---

# Trust boundaries

Identifies where data or authority crosses between users, external services, runtime components, secrets, and stores. A boundary means the receiving side must validate or constrain the crossing; it does not imply that the two sides are independently secure.

## Boundary map

| Boundary | What crosses it | Implemented or declared control | Residual trust or limitation |
| --- | --- | --- | --- |
| Browser to public proxy | HTTPS requests, bearer tokens, survey-link tokens, and respondent cookies | Caddy terminates TLS, removes its `Server` header, adds HSTS and selected browser headers, and proxies only to the configured backend | Caddy and its host can observe request contents after TLS termination; live DNS, certificate issuance, and deployment state were not verified |
| Public proxy to backend | Plain HTTP requests on private port 5000, including credentials and response data | CDK security groups admit backend traffic from the proxy group; Compose binds to the app private IP | TLS is not end-to-end; confidentiality of this hop depends on the VPC, hosts, and security-group deployment matching the definitions |
| Browser to Auth0 and API | Login state, Auth0 access and ID tokens | Auth0 issues tokens; the API verifies access tokens and validates ID-token signature and selected claims during bootstrap | Auth0, its configuration, browser redirect handling, and token storage are external trust dependencies |
| Anonymous respondent to API | Public slug or bearer link, answer commands, session and recognition cookies | Access rules enforce survey publication/visibility and link state; session and recognition tokens are stored only as hashes; cookies are `Secure`, `HttpOnly`, and `SameSite=Lax` | General/public access intentionally permits anonymity; link tokens are bearer credentials stored plaintext in core data; explicit CSRF tokens were not found |
| Authenticated operator to Studio API | Auth0 subject plus project/survey identifiers and commands | Route authentication and local project/survey permission decorators; database-scoped access lookups | Complete decorator coverage was not audited; `platform_admin` bypasses membership checks |
| Backend to Auth0 | OIDC discovery/JWKS reads and Management API operations | TLS client calls, configured issuer/audience/client values, separate Management API machine secret | Availability and correctness of Auth0 and outbound DNS/TLS remain trusted; management operations grant the backend authority over external accounts |
| Backend to core database | Accounts, authorization, projects, surveys, subjects, links, session metadata, answer slots, and wrapped survey keys | Separate core engine and credential; ORM/domain checks plus SQL constraints | The backend has broad read/write authority; core contains identity and linkability metadata, plaintext survey-link tokens, and wrapped key material |
| Backend to response database | Opaque locators, wrapped session keys, ciphertext, and nonces | Separate response engine and credential; response schema omits core foreign keys and direct identity identifiers | The same backend process opens both databases and can reconstruct locators and decrypt answers, so this is data separation rather than backend privilege separation |
| Core database to response database | No direct database connection; relationship is reconstructed through derived locators | HMAC-SHA256 locators use a versioned linkage secret outside both databases | Compromise of a database plus linkage/key material changes the exposure; cross-database transaction atomicity is coordinated in application code rather than by one database transaction |
| Backend to KMS and Secrets Manager | Survey-key wrap/unwrap requests and versioned linkage-secret reads | IAM role grants, KMS encryption context, configured secret ARN, worker caches | AWS APIs and IAM configuration are trusted; plaintext keys and linkage material exist in backend memory while used or cached |
| Authorized results reader through backend | Result request and optionally decrypted answer values | `submission:view` permission on Studio result routes; backend resolves locators and decrypts response rows | Authorization protects API access, but the backend and its logs/memory become plaintext handling points; downstream browser/export handling was not reviewed here |
| App host to outbound proxy | Auth0 and selected AWS HTTPS traffic | Private app subnet, no NAT in the definition, Squid source/CONNECT/domain allow-list, proxy security-group rules | Squid and proxy host can observe destinations and traffic metadata; the allow-list contains deployment placeholders that must be rendered correctly |
| Backend container to host-provided secrets | Database passwords, Flask secret, and Auth0 Management API secret files | Bootstrap fetches into root-owned tmpfs files; Compose mounts read-only secrets; container filesystem is read-only with reduced capabilities | Root/host compromise can read or replace secrets; correct bootstrap attachment to CDK instances is not implemented in `ApplicationStack` |
| Frontend deployment workflow to AWS | Built frontend artifacts, staging S3 writes, CloudFront invalidations, and SSM parameter reads | GitHub OIDC assumes the declared deployment role rather than storing long-lived AWS credentials | The checked-in workflow is staging-only; it does not deploy CDK stacks, backend images, database changes, or production |

## Data-store boundary

The core database owns identity, authorization, survey structure, link access, subject/session metadata, answer slots, and wrapped survey branch keys. The response database owns anonymous envelopes and encrypted current answers. It has no schema-level foreign keys to core and receives opaque locators rather than core identifiers. This limits the meaning of a response-database-only disclosure.

The boundary is intentionally crossed inside the backend through non-atomic,
application-coordinated writes and reads. Transaction order, compensation,
reconciliation, and administrative retrieval belong in [[Data flows]] and
[[Responses and encryption]].

## Identity boundary

Auth0 proves possession of an external account token; FlowForm then maps its `sub` to a local user and applies local authorization. An authenticated Auth0 token alone does not grant project or survey permissions. Conversely, public and link-based respondent access does not require a local operator membership.

Participant identity verification is another explicit crossing: an authenticated survey link is usable only after the assigned participant identity is linked to the same local user. Subject-recognition cookies are not Auth0 authentication and must not be treated as operator credentials. See [[Identity and authentication]] and [[Links and subjects]].

## Network boundary status

The repository contains a coherent target definition for a public proxy EC2 instance, private app EC2 instance, isolated app and RDS subnets, restrictive security groups, Caddy ingress, and Squid-controlled egress. The runtime Compose files implement container hardening and private-address bindings for that shape.

This is not yet a confirmed deployed boundary. `DatabaseStack` contains only TODOs, while `ApplicationStack` creates the instances but leaves runtime user-data/bootstrap attachment for later wiring. Development and test Compose files also publish backend and database ports to the host, so their boundary is the developer machine rather than the EC2 topology. See [[Deployment model]] and [[Local infrastructure]].

## Header and client-address trust

Caddy is intended to be the only network caller of the deployed backend, but the application itself accepts the first `X-Forwarded-For` value as the client IP without a trusted-proxy list. Request logging and the in-memory rate limiter use that value. The security-group boundary is therefore part of the correctness of client attribution; direct backend reachability or unfiltered forwarding would allow caller-controlled attribution.

CORS is initialized for API routes with credentials enabled and falls back to wildcard origins unless `CORS_ORIGINS` is supplied through Flask configuration. No typed environment mapping for that value was found. Browser-origin and CSRF assumptions remain unresolved in [[Security model]].

## Open questions

- Is TLS required between Caddy and the private backend, or is security-group/VPC isolation the accepted boundary?
- Which component normalizes or overwrites forwarding headers, and should Flask explicitly trust only the proxy address?
- What production values replace the Squid allow-list placeholders, and how is attempted egress outside the list monitored?
- Will core and response data use separate RDS instances, one instance with separate databases, or another arrangement? `DatabaseStack` has not selected or implemented it.
- How will CDK attach and update the checked-in bootstrap/cloud-init resources, and how will deployment verify private addressing, tmpfs secrets, and container hardening?
- What controls apply to plaintext responses after authorized decryption in browser views, exports, logs, caches, and support workflows?

## Related documents

- [[Security model]]
- [[System context]]
- [[Data flows]]
- [[Deployment model]]
- [[Runtime containers]]
- [[Identity and authentication]]
- [[Responses and encryption]]
- [[Secrets and configuration]]
