---
title: Security model
aliases:
  - "Security model"
document_type: architecture
status: draft
authority: canonical
verified_against_commit: null
tags: [backend, infrastructure, security]
related_code:
  - "../../backend/app/middleware/auth/"
  - "../../backend/app/services/access/access_service.py"
  - "../../backend/app/services/public_submissions/"
  - "../../backend/app/crypto/"
  - "../../backend/app/core/config.py"
  - "../../backend/app/middleware/rate_limit/"
  - "../../infra/containers/"
  - "../../infra/deployment/aws/cdk/flowform_infra/stacks/"
  - "../../.github/workflows/ci.yml"
  - "../../backend/scripts/run_backend_security.sh"
related_docs:
  - "Trust boundaries"
  - "Identity and authentication"
  - "Projects and access"
  - "Links and subjects"
  - "Responses and encryption"
  - "Secrets and configuration"
  - "Deployment model"
---

# Security model

Explains the security controls visible in the current implementation and the limits of the evidence. It is an architectural summary, not a complete threat model, penetration-test result, compliance statement, or deployment attestation.

## Security objectives visible in the design

FlowForm separates operator access from respondent access, scopes operator authorization to projects and surveys, avoids storing raw respondent session and recognition tokens, encrypts answer payloads, and keeps identity-bearing core records out of the response database. The intended deployed network places a public reverse proxy in front of a private application host and restricts application egress.

These controls reduce exposure but do not prove confidentiality, integrity, or availability against every threat. Their concrete crossings and residual trust are summarized in [[trust-boundaries|Trust boundaries]].

## Authentication and identity

Auth0 is the external identity provider for operator accounts and authenticated respondent flows. Protected Flask routes use `AuthExtension.require_auth()` to extract a bearer token and ask the configured Auth0 API client to verify it for the configured domain and audience. Optional-auth routes accept no token, but reject an invalid token when one is supplied.

Initial local-user bootstrap additionally verifies an Auth0 ID token with an RS256 JWKS key and checks issuer, client audience, expiry, issued-at presence, and equality between the access-token and ID-token subjects. The local `users.auth0_user_id` then maps the external identity to FlowForm's authorization records. Account-management operations can use a separate Auth0 Management API machine credential. Deeper identity lifecycle detail belongs in [[identity-and-authentication|Identity and authentication]].

## Authorization

Studio authorization is stored locally as project memberships, project roles, survey role overrides, and named permissions. Project and survey route decorators load the authenticated local actor, calculate access for the route's project and survey identifiers, and reject missing membership or permission. A `platform_admin` user bypasses those membership checks; administration and assignment of that flag were not established in this pass.

Respondent access uses a separate policy path rather than Studio RBAC. Public slugs require a public, published survey. Survey links are bearer credentials whose active, expiry, use, visibility, link-type, and participant-assignment rules are checked before resolution and session start. Authenticated links additionally require a local user matching the assigned participant identity. See [[projects-and-access|Projects and access]] and [[links-and-subjects|Links and subjects]].

This review verified the authorization mechanisms and representative route use, not complete decorator coverage for every endpoint.

## Browser-held credentials

Submission-session and subject-recognition tokens are generated from cryptographic randomness. Only SHA-256 hashes are stored in core data; the raw tokens are returned as `Secure`, `HttpOnly`, `SameSite=Lax` cookies with respondent-path scoping and explicit lifetimes. Session commands load the core session by the token hash and enforce expiry and lifecycle state.

Survey-link bearer tokens differ: the current `survey_links` schema stores the token itself so it can be resolved directly. Possession of a valid link can therefore grant the access allowed by its link type and state.

No explicit CSRF token mechanism was found for cookie-authenticated respondent commands. The observed browser controls are cookie attributes, path scoping, and CORS. CORS supports credentials and defaults to `*` when `CORS_ORIGINS` is not injected into Flask configuration; no typed settings field or deployed value for that key was found. These behaviours need a dedicated browser-security review before stronger claims are made.

## Response confidentiality and linkage

Answer protection uses a three-tier key hierarchy:

1. AWS KMS wraps one survey branch key, stored in core data.
2. The survey branch key wraps one session data-encryption key, stored in the response envelope.
3. The session key encrypts answer payloads with AES-256-GCM and context-derived additional authenticated data.

Plaintext survey and session keys can be cached in backend worker memory. Opaque session and answer locators are HMAC-SHA256 values derived from core UUIDs with a separately versioned linkage secret fetched from AWS Secrets Manager. The response schema contains envelopes and encrypted current answers without foreign keys or direct identifiers back to core data. See [[responses-and-encryption|Responses and encryption]].

The backend remains trusted across this split: it opens both database sessions, can obtain the linkage and encryption keys, and decrypts answers for authorized result reads. The split limits what either database contains by itself; it does not protect answers from a fully compromised backend process.

## Secrets and key access

Backend configuration supports file-backed database passwords, Flask secret key, and Auth0 Management API secret. The runtime bootstrap materializes those values from Secrets Manager into a root-owned tmpfs directory with mode `0700` and files with mode `0600`; Compose mounts them read-only under `/run/secrets`. Non-secret runtime configuration is rendered separately from SSM Parameter Store.

The CDK security stack defines KMS and Secrets Manager resources plus an application role with read access to the declared secrets, KMS encrypt/decrypt, SES send, scoped SSM reads, and ECR pull access. ECR repository grants still use a name wildcard that the source marks for tightening. Runtime crypto also lets the backend call KMS and fetch versioned linkage secrets directly. Operational handling and rotation belong in [[secrets-and-configuration|Secrets and configuration]].

Dev and production backend processes fail closed during initialization unless
the configured Auth0 management credential can obtain a token, the linkage
secret's current version can be read, and the configured KMS key completes an
encrypt/decrypt round trip. Test mode skips these outbound probes. SES access is
not boot-probed because a send would be externally visible.

File-backed delivery protects against placing these values directly in normal container environment variables, but does not by itself prove secure secret creation, rotation, host access, backup handling, or absence from process memory.

## Network and runtime controls

The staging/production definitions place Caddy on a public proxy instance and the Flask/Gunicorn backend on an application instance without a public IP. Caddy exposes ports 80 and 443, obtains TLS certificates through Route 53 DNS, adds HSTS, content-type, and referrer-policy headers, and forwards to the backend's private address on HTTP port 5000. Security groups restrict backend ingress to the proxy group.

The application subnet has no NAT gateway in the CDK definition. Outbound HTTPS is routed through Squid on the proxy host, with source, port, and domain allow-lists; RDS traffic and selected VPC services use separate paths. Runtime Compose drops Linux capabilities, enables `no-new-privileges`, uses read-only container filesystems and tmpfs writable areas, and limits backend PIDs. See [[deployment-model|Deployment model]] and [[runtime-containers|Runtime containers]].

These are repository-defined controls, not confirmation of a live environment. The CDK database stack remains an unimplemented scaffold, and the application stack creates instances but does not yet attach the runtime bootstrap/user-data wiring described in its comments.

## Abuse and input controls

The application registers a configurable in-memory, per-IP sliding-window rate limiter. It is local to each worker process and trusts the first `X-Forwarded-For` value whenever present, so it is not a distributed quota and depends on direct backend access being blocked and proxy header behaviour being controlled. Request models, domain rules, and database constraints provide additional input and integrity checks, but are not substitutes for authorization or a threat review.

## Open questions

- Which production origins will populate `CORS_ORIGINS`, and what CSRF policy is intended for cookie-authenticated respondent writes?
- How is `platform_admin` granted, audited, and revoked?
- Should survey-link bearer tokens be stored as hashes rather than plaintext, and what rotation/revocation process applies after disclosure?
- What distributed or edge-level abuse protection is intended beyond the current per-process rate limiter?
- Are plaintext-key cache lifetime, eviction on session completion, worker memory exposure, and key rotation covered by operational policy and tests?
- When the database and application stacks are completed, which controls will prove RDS encryption, credential separation, backups, deletion protection, and runtime bootstrap attachment?
- CI runs exact-lock Python dependency auditing and Bandit for the backend plus
  a low-threshold pnpm audit for frontend changes. This is not comprehensive
  repository or deployed-image scanning, and no evidence in this pass
  establishes security-event alerting, audit-log retention, incident response,
  backup restore testing, or formal threat-model coverage.

## Related documents

- [[trust-boundaries|Trust boundaries]]
- [[identity-and-authentication|Identity and authentication]]
- [[projects-and-access|Projects and access]]
- [[links-and-subjects|Links and subjects]]
- [[responses-and-encryption|Responses and encryption]]
- [[secrets-and-configuration|Secrets and configuration]]
- [[deployment-model|Deployment model]]
