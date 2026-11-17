# FlowForm security audit

**Verdict: FlowForm does not currently meet a reasonable production security bar.** I confirmed several exploitable authorization flaws, an account/invitation takeover path, exposed cryptographic and database material, and high-risk infrastructure configuration.

This was a read-only audit of branch `feature` at commit `ad26b87e9820` on 22 July 2026. I did not test exposed credentials, attack a deployed environment, rotate anything, or modify application code.

A source audit cannot honestly guarantee that “all zero-days” have been found—unknown vulnerabilities cannot be proven absent. This is the complete defensible finding set from the repository, local state, tests, dependency scans, and reachable Git history.

## Immediate containment recommendations

No action below was performed.

1. Treat the exposed linkage secret, 29 plaintext data-encryption keys, survey token, database passwords, Auth0 management secret, Grafana token, and Proxmox tokens as potentially compromised.
2. Re-encrypt records protected by the exposed DEKs. Rotating the KMS master key alone does not invalidate leaked plaintext DEKs.
3. Plan a versioned linkage-secret migration; blindly replacing it could destroy legitimate pseudonymous linkage.
4. Revoke the exposed survey link and inventory the disclosed AWS access-key ID.
5. Remove sensitive logs from active branch tips, then coordinate a full history rewrite, fork/cache cleanup, and credential rotation.
6. Replace every committed rehearsal CA and leaf key. Do not continue trusting that CA globally.
7. Disable the public test-email endpoint and prioritize the email-verification, suspended-member, results-deletion, and role-escalation fixes.

## Critical or urgent exposures

1. **Secrets embedded in local Terraform state — Critical if active**

   `infra/deployment/proxmox/terraform/terraform.tfstate` and its backup contain non-placeholder Auth0 management and Grafana credentials. State is local, unencrypted, unlocked, and mode `0644`. Grafana material also exists in `infra/env/dev/.grafana.env`.

   Cloud-init propagates these values through [localstack.yaml.tftpl](/home/shayman86/my-repos/FlowForm/infra/deployment/proxmox/cloud-init/templates/localstack.yaml.tftpl:16), and [bootstrap-proxy.sh](/home/shayman86/my-repos/FlowForm/infra/deployment/proxmox/bootstrap/bootstrap-proxy.sh:59) creates a proxy environment file readable as `0644`.

   Move state to an encrypted, access-controlled backend; stop placing secrets in cloud-init/state where possible; write guest secret files as `0600`; rotate existing values.

2. **Cryptographic keys, bearer credentials, database passwords, and PII committed in logs — High/Critical**

   `backend/logs/app.log.1` was committed three separate times:

   - May 7 blob: user PII and credential-bearing database URLs.
   - June 24 blob: one raw linkage secret, **29 plaintext KMS DEKs**, corresponding ciphertext metadata, one raw survey-link bearer token, database passwords, AWS access-key ID, 195 complete but now-expired SigV4 headers, and pseudonymous session metadata.
   - June 30 blob: personal invitation data, the same survey token, and database credentials.

   Two distinct database passwords match current dev/test secret files. Current ignored `backend/logs/app.log` still contains 24 credential-bearing database URLs. The AWS secret-access key itself, JWTs, cookies, and OAuth tokens were not found.

   Locally cached `origin/main` and `origin/staging` tips still contain the June 30 blob. Those refs were not fetched and may be stale, but the blobs remain reachable through history regardless.

   The root cause remains: [.gitignore](/home/shayman86/my-repos/FlowForm/.gitignore:76) ignores `*.log`, but not `.log.1` through `.log.5`, which are produced by [logging_config.py](/home/shayman86/my-repos/FlowForm/backend/app/logging/logging_config.py:154). Add comprehensive log exclusions, structured redaction, secret scanning, and `0600` file creation.

3. **Committed unconstrained rehearsal CA private key — High**

   A tracked root CA and related keys are under `infra/containers/strategies/rehearsal/services/tls-shim/ca/`. The CA is installed globally by [app.yaml.tftpl](/home/shayman86/my-repos/FlowForm/infra/deployment/proxmox/cloud-init/templates/app.yaml.tftpl:27) and [proxy.yaml.tftpl](/home/shayman86/my-repos/FlowForm/infra/deployment/proxmox/cloud-init/templates/proxy.yaml.tftpl:28). Rehearsal permits real Auth0 traffic through [allowed-domains.txt](/home/shayman86/my-repos/FlowForm/infra/containers/strategies/rehearsal/services/squid/allowed-domains.txt:14).

   Anyone possessing that key and a MITM position can issue certificates trusted by rehearsal hosts, including for Auth0 endpoints. Generate per-environment keys outside Git and avoid globally trusting an unconstrained rehearsal CA.

4. **Proxmox TLS verification disabled while API tokens are stored locally — High**

   The active ignored Terraform variables disable certificate verification; [providers.tf](/home/shayman86/my-repos/FlowForm/infra/deployment/proxmox/terraform/providers.tf:1) passes that choice directly to the provider. Packer also defaults to insecure TLS in [proxmox.pkr.hcl](/home/shayman86/my-repos/FlowForm/infra/images/packer/variables/proxmox.pkr.hcl:112).

   This permits credential interception or malicious build/deployment responses. Install the Proxmox CA, require verification, and rotate tokens after correcting trust.

## Confirmed high-severity vulnerabilities

5. **Email-change verification desynchronization enables invitation theft**

   Email change requires only ordinary bearer authentication in [profile.py](/home/shayman86/my-repos/FlowForm/backend/app/api/v1/account/profile.py:65). Auth0 resets verification, but [account.py](/home/shayman86/my-repos/FlowForm/backend/app/services/account.py:94) updates only the local email. The stale local `email_verified=true` then causes invitation processing in [members.py](/home/shayman86/my-repos/FlowForm/backend/app/services/members.py:130) to skip live verification.

   An already-verified user can change to an unregistered victim invitation address, list that address’s invitations, and accept one without controlling its mailbox. Impact can reach project administration.

6. **Participant identity linking accepts unverified accounts**

   [participants.py](/home/shayman86/my-repos/FlowForm/backend/app/services/participants.py:133) compares email addresses but never requires `user.email_verified`. It then stores the association as verified.

   An unverified Auth0 account using an assigned participant email and a valid respondent link can permanently bind itself to the victim’s participant/subject identity.

7. **Suspended members retain all permissions**

   [access_repo.py](/home/shayman86/my-repos/FlowForm/backend/app/repositories/access_repo.py:25) loads memberships without filtering their status, and [access_service.py](/home/shayman86/my-repos/FlowForm/backend/app/services/access/access_service.py:102) continues granting role permissions.

   Suspension therefore has no authorization effect.

8. **Read-only result viewers can permanently delete submissions**

   DELETE in [results.py](/home/shayman86/my-repos/FlowForm/backend/app/api/v1/studio/surveys/results.py:124) requires only `submission:view`. The permission model has no separate deletion permission in [permissions.py](/home/shayman86/my-repos/FlowForm/backend/app/domain/permissions.py:59).

   Any results-viewing role can destroy response data.

9. **View-only collaborators receive live respondent tokens and PII**

   Listing access links requires only `survey:view` in [access_links.py](/home/shayman86/my-repos/FlowForm/backend/app/api/v1/studio/surveys/access_links.py:27). The response includes the raw bearer token, participant ID, and email in [survey_access_links.py](/home/shayman86/my-repos/FlowForm/backend/app/schema/api/responses/survey_access_links.py:13).

   A viewer can impersonate an assigned respondent, submit false data, or consume a single-use link. Store hashes, reveal tokens only once, and require a manage-links permission.

10. **Custom and survey role self-escalation**

   A custom role containing only `project:manage_roles` can add every permission to itself through [roles.py](/home/shayman86/my-repos/FlowForm/backend/app/services/roles.py:41). Separately, survey members with `project:manage_members` can self-assign existing privileged survey roles through [survey_members.py](/home/shayman86/my-repos/FlowForm/backend/app/services/survey_members.py:61).

   Enforce an actor privilege ceiling and prohibit self-assignment/escalation.

11. **Unauthenticated email relay**

   [health.py](/home/shayman86/my-repos/FlowForm/backend/app/api/v1/system/health.py:66) exposes a public POST endpoint accepting an arbitrary recipient and sending through SES. The blueprint is always registered, and the rate limit is memory-only and per worker.

   When email is enabled—which is the default—this supports email bombing, cost abuse, reputation damage, and possible SES suspension.

12. **Overbroad GitHub OIDC trust executes PR-controlled infrastructure code**

   [security_stack.py](/home/shayman86/my-repos/FlowForm/infra/deployment/aws/cdk/flowform_infra/stacks/security_stack.py:224) trusts `repo:<owner>/<repo>:*`, while the preview role receives AWS `ReadOnlyAccess`. [ci.yml](/home/shayman86/my-repos/FlowForm/.github/workflows/ci.yml:397) obtains OIDC credentials before running repository-controlled CDK/Python.

   A malicious same-repository PR, branch, or workflow modification can obtain broad AWS read access. Restrict exact protected refs/environments and scope the IAM role to the resources required for preview.

13. **Docker socket mounts provide host-root-equivalent access**

   Root-running Alloy containers mount `/var/run/docker.sock` in [app.yml](/home/shayman86/my-repos/FlowForm/infra/containers/runtime/compose/app.yml:79) and [proxy.yml](/home/shayman86/my-repos/FlowForm/infra/containers/runtime/compose/proxy.yml:108). `:ro` does not limit Docker API operations. The rehearsal LocalStack fixture mounts it writable in [compose.localstack.yml](/home/shayman86/my-repos/FlowForm/infra/containers/strategies/rehearsal/fixtures/compose.localstack.yml:18).

14. **Flask debugger exposed to the LAN in development**

   [compose.yml](/home/shayman86/my-repos/FlowForm/infra/containers/strategies/dev/compose/compose.yml:75) runs Flask debug mode on `0.0.0.0`, publishes port 5000, runs as root, and mounts source, secrets, and the host AWS token cache writable.

   Bind development to loopback, disable the interactive debugger outside an isolated workstation, run non-root, and remove the AWS cache mount.

## Medium-severity vulnerabilities and weaknesses

15. **No recent-authentication check for account takeover operations.** Email change, password-reset ticket creation, MFA removal, and account deletion require only an ordinary access token in [profile.py](/home/shayman86/my-repos/FlowForm/backend/app/api/v1/account/profile.py:65). Require recent `auth_time`, MFA, or a dedicated step-up credential.

16. **Single-use respondent links are raceable.** Link state is checked without locking, the session is created first, and consumption is unconditional in [public_link_repo.py](/home/shayman86/my-repos/FlowForm/backend/app/repositories/public_link_repo.py:100) and [session_starter.py](/home/shayman86/my-repos/FlowForm/backend/app/services/public_submissions/core/actions/session_starter.py:97). Use a conditional database update or row lock plus a uniqueness constraint.

17. **Invitation acceptance is raceable, and invitation credentials never expire.** Creation and resolution in [invitations_repo.py](/home/shayman86/my-repos/FlowForm/backend/app/repositories/invitations_repo.py:53) do not enforce `expires_at`; concurrent accounts sharing an email can both pass acceptance before state is committed.

18. **Account deletion can delete Auth0 first and then fail locally.** [account.py](/home/shayman86/my-repos/FlowForm/backend/app/services/account.py:158) removes the Auth0 identity before local deletion, but assigned survey-link constraints can reject the local transaction. The result is an Auth0-deleted user whose FlowForm data remains.

19. **Cross-database operations can produce inconsistent erasure.** Result deletion commits the response database before core state in [admin_results/service.py](/home/shayman86/my-repos/FlowForm/backend/app/services/admin_results/service.py:186). Project/survey deletion removes core keys but leaves response ciphertext indefinitely. Session-start compensation can also leave unreconciled response envelopes.

20. **Public submission event abuse.** The cookie-authenticated event endpoint in [submission_sessions.py](/home/shayman86/my-repos/FlowForm/backend/app/api/v1/respondent/submission_sessions.py:93) permits duplicate events indefinitely. Per-worker caching can also accept events for up to 30 minutes after another worker completes the session. This enables analytics poisoning and database growth.

21. **Arbitrary credentialed CORS and no explicit CSRF/origin enforcement.** [extensions.py](/home/shayman86/my-repos/FlowForm/backend/app/core/extensions.py:35) configures wildcard origins with credentials. SameSite=Lax cookies help, but a compromised or attacker-controlled sibling origin can make credentialed respondent mutations.

22. **Rate limits are per-process, resettable, and memory-unbounded.** [general.py](/home/shayman86/my-repos/FlowForm/backend/app/utils/general.py:11) trusts the first forwarded IP, while [rate_limit/service.py](/home/shayman86/my-repos/FlowForm/backend/app/middleware/rate_limit/service.py:25) never evicts source entries. Direct-backend deployments permit spoofing and memory growth.

23. **No request-body size limit before JSON parsing.** [validation.py](/home/shayman86/my-repos/FlowForm/backend/app/api/utils/validation.py:10) allocates the body before model validation, with no Flask or Caddy body cap. A small synchronous Gunicorn pool magnifies the availability risk.

24. **Server accepts empty/incomplete survey completion.** [completion.py](/home/shayman86/my-repos/FlowForm/backend/app/services/public_submissions/core/actions/completion.py:35) changes state without validating required visible questions. Required-answer enforcement exists only in the browser.

25. **CSV formula injection.** Survey question keys permit spreadsheet formula prefixes and are emitted directly by [export.py](/home/shayman86/my-repos/FlowForm/backend/app/services/admin_results/core/export.py:30). A malicious editor can target a user who opens the resulting CSV.

26. **Credential-bearing invitation URLs.** Tokens appear in API and frontend path components, do not expire, and can be retained in browser history and warning/error logs. See [invitations.py](/home/shayman86/my-repos/FlowForm/backend/app/api/v1/account/invitations.py:57) and the [frontend route](/home/shayman86/my-repos/FlowForm/frontend/apps/studio-app/src/routes/_public/invitations/$token.tsx:4).

27. **Missing CSP, anti-framing, and frontend security headers.** [static_site_construct.py](/home/shayman86/my-repos/FlowForm/infra/deployment/aws/cdk/flowform_infra/constructs/static_site_construct.py:82) configures caching but no CSP, `frame-ancestors`, HSTS, nosniff, referrer, or permissions policy.

28. **Access and refresh tokens persist in localStorage.** [main.tsx](/home/shayman86/my-repos/FlowForm/frontend/apps/studio-app/src/main.tsx:24) configures Auth0 localStorage caching and refresh tokens. I did not find a current exploitable XSS sink, but any future same-origin XSS or compromised frontend dependency gains durable credentials.

29. **Additional infrastructure weaknesses.**

   - Whole-account nonproduction role with secrets/KMS/SES access: [security_stack.py](/home/shayman86/my-repos/FlowForm/infra/deployment/aws/cdk/flowform_infra/stacks/security_stack.py:164).
   - Unauthenticated plaintext Alloy ingestion: [config.alloy](/home/shayman86/my-repos/FlowForm/infra/containers/runtime/services/alloy/config.alloy:39).
   - Direct rehearsal backend bypass around Caddy and an anonymous mutable/deletable registry: [compose.registry.yml](/home/shayman86/my-repos/FlowForm/infra/containers/strategies/rehearsal/fixtures/compose.registry.yml:27).
   - SSH scripts disable host-key verification, for example [verify.sh](/home/shayman86/my-repos/FlowForm/infra/deployment/proxmox/scripts/verify.sh:61).
   - Mutable image/action tags, unsigned installer downloads, and open-ended Packer plugins.
   - CI references stale pre-reorganization paths and lacks secret, IaC, container, CodeQL, SBOM, provenance, and signing gates.

30. **Lower-risk privacy and hardening issues.**

   - Export builds/decrypts up to 10,000 sessions in memory instead of truly streaming.
   - Public DTOs expose unnecessary project/store/version/creator identifiers.
   - Logout does not reliably await query-cache cleanup or remove saved survey drafts.
   - Provider/database exception text and Pydantic rejected input can enter logs.
   - Plaintext linkage/survey/session keys remain cached after completion.
   - Manual ID-token verification lacks nonce, multi-audience `azp`, `nbf`, future-`iat`, `auth_time`, and robust JWKS refresh handling.
   - Core/response DSNs are not required to differ, and database initialization does not explicitly revoke PostgreSQL `PUBLIC CONNECT`.

## Known vulnerable dependencies

Fresh scans on 22 July 2026 found:

- **Backend:** Authlib `1.7.0` has CVE-2026-41479 and CVE-2026-44681; Click `8.3.1` has CVE-2026-7246. The affected Authlib authorization-server paths and `click.edit` were not found in FlowForm’s runtime path, but the locks should be upgraded. Click’s maintainers document the relevant `shell=True` removal in [8.3.3](https://github.com/pallets/click/blob/main/CHANGES.rst#version-833).
- **Frontend:** `pnpm audit` reported **11 advisories: 8 high, 2 moderate, 1 low, 0 critical**. Packages include Astro, `js-yaml`, `brace-expansion`, `fast-uri`, `svgo`, and `sharp`. FlowForm’s Astro site is statically generated and I did not find the attacker-controlled SSR inputs required by the three reported Astro XSS paths, but the installed version is still within the affected ranges. See the maintainer advisories for [transition properties](https://github.com/withastro/astro/security/advisories/GHSA-4g3v-8h47-v7g6), [custom-element attributes](https://github.com/withastro/astro/security/advisories/GHSA-f48w-9m4c-m7f5), and [hydrated transition directives](https://github.com/withastro/astro/security/advisories/GHSA-7pw4-f3q4-r2p2).
- **Developer MCP:** its lock contains advisories affecting `cryptography`, `joserfc`, `mcp`, `pydantic-settings`, `PyJWT`, `python-multipart`, and `starlette`. Normal use is local stdio, making several HTTP-server advisories unreachable, but this tooling handles authentication material and should be upgraded.
- The backend audit script resolves fresh requirements rather than auditing the exact production lock used by `uv sync --frozen`, so CI can miss deployed vulnerable pins.

## Security controls that are working

- Response records use opaque HMAC locators, ciphertext, nonces, and wrapped keys rather than direct user, project, survey, subject, or email identifiers.
- Core and response databases use separate SQLAlchemy bases, engines, and session makers.
- AES-256-GCM uses fresh 12-byte nonces, KMS-wrapped random survey keys, and contextual AAD.
- No cryptographic break, dynamically constructed SQL injection, request-controlled SSRF, command injection, unsafe deserialization, path traversal, upload vulnerability, or exploitable stored/reflected XSS was found.
- Session, recognition, and invitation tokens use strong randomness and are generally hashed at rest. Respondent cookies are Secure, HttpOnly, host-only, path-scoped, and SameSite=Lax.
- JWT access-token verification fixes RS256 and validates signature, issuer, audience, and expiry.
- Production AWS definitions include private/isolated networking, default-deny security groups, IMDSv2, encrypted EBS, rotating KMS keys, private S3 origins, CloudFront OAC, and modern TLS.
- Production containers generally drop capabilities, use `no-new-privileges`, and use read-only filesystems—although the Docker-socket exceptions negate that protection for Alloy.

## Validation and limitations

- 87 routes inventoried: 76 authenticated, 2 optional-auth, and 9 intentionally public/token/cookie based. The inappropriate critical public route was `/system/test-email`.
- Backend unit suite: **218 passed**.
- Targeted crypto/schema suite: **84 passed**.
- Bandit: no medium/high severity and confidence findings.
- Terraform formatting, Packer formatting, and Bash syntax checks passed.
- Microproofs confirmed arbitrary credentialed CORS behavior and CSV formula output.
- No live Auth0 tenant, AWS account, Proxmox host, deployed database, or external endpoint was attacked.
- Integration/e2e testing was not run because the required database containers were not running and starting infrastructure would have changed machine state.
- AWS database and observability stacks remain scaffolds, so actual production backups, monitoring, alerting, deletion, and database controls cannot be certified.

## Workspace integrity

The worktree was clean when the audit began. It became dirty concurrently during the audit:

```text
 M .gitignore
 M scripts/tools/count_lines.sh
```

I did not create or revert either change. Their attribution is unknown, and they are not audit deliverables. No FlowForm source, configuration, secret, certificate, state, or documentation file was intentionally changed by this audit.