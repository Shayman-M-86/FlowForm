# FlowForm security audit verdict

**FAIL — FlowForm is not production-ready in its current state.**

At commit `ad26b87e98207763669367a2e9b70ffa2632ce19`, I found **1 Critical and 12 High-severity findings**, plus multiple Medium and Low risks.

I cannot honestly certify that “all zero-days” have been listed. Undisclosed flaws cannot be proven absent. What I can say is that I completed a broad read-only audit of the application code, Git history, dependencies, frontend, infrastructure, CI/CD, and current GitHub settings. No unauthenticated RCE, SQL injection, JWT signature bypass, or broken encryption primitive was found.

## Immediate containment

1. **Remove the FlowForm rehearsal CA from every Windows, WSL, Firefox, Node, and other trust store.** The certificate is named `FlowForm Rehearsal CA (throwaway)`, SHA-1 fingerprint `12:BB:64:D7:71:D1:3E:F3:EA:EE:54:22:C4:DA:3C:64:E6:7B:68:D5`.
2. **Treat the historical linkage key as compromised.** Rotate it, preserve access to old data through a controlled migration, and investigate access. Simply advancing `AWSCURRENT` does not protect records that still use the exposed old version.
3. **Revoke every pending project invitation and reissue it.** At least two unique raw invitation tokens are recoverable from public Git history, and invitations currently do not expire.
4. **Rotate the Auth0 Management and Grafana credentials** if they have passed through rehearsal, Terraform/cloud-init, or unprotected CI.
5. **Disable or narrow the GitHub OIDC roles and the `backend-test` secret-bearing PR job** until branch, environment, and subject restrictions are in place.
6. Only after rotation/revocation, coordinate a Git-history rewrite and require fresh clones. History deletion alone does not invalidate leaked material.

## Critical and High findings

| Severity | Finding | Impact and evidence |
|---|---|---|
| **Critical** | Public Git history contains a plaintext linkage HMAC key | The [public repository](https://github.com/Shayman-M-86/FlowForm) contains 137 real Secrets Manager response records in historical commit `74c0fc71`, including the plaintext `flowform/dev/linkage-secret`. The key derives cross-database locators in [locators.py](/home/shayman86/my-repos/FlowForm/backend/app/crypto/_internal/locators.py:8), while old versions remain retrievable. This compromises the intended pseudonymous database boundary if an attacker obtains database identifiers. Current rotation status is unknown, so it must be treated as exposed. |
| **High; Critical on trusting workstations** | Public CA private key recommended as a global trust root | [rehearsal-ca.key](/home/shayman86/my-repos/FlowForm/infra/containers/strategies/rehearsal/services/tls-shim/ca/rehearsal-ca.key) is public, unrestricted, valid until 2036, and its certificate is explicitly recommended for Windows Trusted Root installation in [proxmox-rehearsal-setup.md](/home/shayman86/my-repos/FlowForm/docs/40-implementation/proxmox-rehearsal-setup.md:114). Anyone can sign a certificate for any hostname that those machines trust. |
| **High** | GitHub OIDC trusts every ref and workflow | Both deployment and preview roles accept `repo:Shayman-M-86/FlowForm:*` in [security_stack.py](/home/shayman86/my-repos/FlowForm/infra/deployment/aws/cdk/flowform_infra/stacks/security_stack.py:224). Current GitHub API checks also showed unprotected `main`/`staging` branches and unrestricted Actions. Repository-controlled workflow code can bypass the intended deployment workflow and potentially deploy malicious Studio code or read account-wide AWS metadata. |
| **High** | Real Auth0 Management secret exposed to PR code | `backend-test` injects the real secret before executing repository-controlled scripts, Dockerfiles and tests in [ci.yml](/home/shayman86/my-repos/FlowForm/.github/workflows/ci.yml:172). The live `test` GitHub environment has no reviewers or branch restrictions. A malicious same-repository PR can exfiltrate a credential intended to carry user create/delete/update, MFA removal, and ticket scopes. |
| **High** | Docker socket grants host control | Root-running Alloy mounts `docker.sock` in [app.yml](/home/shayman86/my-repos/FlowForm/infra/containers/runtime/compose/app.yml:85) and [proxy.yml](/home/shayman86/my-repos/FlowForm/infra/containers/runtime/compose/proxy.yml:110). `:ro` does not restrict Docker API operations; Alloy compromise becomes VM/instance-role compromise. Rehearsal LocalStack has the same problem while receiving a real Auth0 secret. |
| **High, deployment-dependent** | Secrets persisted into Terraform state, cloud-init and Proxmox snippets | Auth0/Grafana secrets flow through [variables.tf](/home/shayman86/my-repos/FlowForm/infra/deployment/proxmox/terraform/variables.tf:167), rendered cloud-init, provider state and guest data. `sensitive=true` only redacts display. If rehearsal has been applied, retained state, plans, snippets and guest cloud-init must be treated as secret-bearing. |
| **High** | Custom-role self-escalation and unsafe delegation | `project:manage_roles` can replace any non-system role’s permissions without checking the actor in [roles.py](/home/shayman86/my-repos/FlowForm/backend/app/services/roles.py:41). A user can add delete/member/result permissions to their own role. `manage_members` can also assign collaborators to stronger custom roles. |
| **High** | Suspension does not revoke access | Membership status is written, but [access_service.py](/home/shayman86/my-repos/FlowForm/backend/app/services/access/access_service.py:102) never requires `active`. Suspended users retain all effective project and survey permissions. |
| **High** | Read-only survey viewers receive respondent bearer tokens | Link listing requires only `survey:view` in [access_links.py](/home/shayman86/my-repos/FlowForm/backend/app/api/v1/studio/surveys/access_links.py:27), while [survey_access_links.py](/home/shayman86/my-repos/FlowForm/backend/app/schema/api/responses/survey_access_links.py:13) returns raw tokens and participant emails. A viewer can impersonate a respondent or consume their single-use link. |
| **High** | Submission viewing permission authorizes deletion | The DELETE endpoint in [results.py](/home/shayman86/my-repos/FlowForm/backend/app/api/v1/studio/surveys/results.py:124) requires only `submission:view`. Any results viewer can irreversibly delete responses. |
| **High** | Stale email verification permits invitation takeover | Email change correctly resets verification in Auth0 but leaves the local value true in [account.py](/home/shayman86/my-repos/FlowForm/backend/app/services/account.py:94). Invitation acceptance trusts that stale value in [members.py](/home/shayman86/my-repos/FlowForm/backend/app/services/members.py:133). A previously verified attacker can change to an invited address and accept without mailbox proof. |
| **High** | “Single-use” survey links are raceable | Used-state is checked before session creation, then updated without a lock or conditional predicate in [public_link_repo.py](/home/shayman86/my-repos/FlowForm/backend/app/repositories/public_link_repo.py:100). Concurrent requests can both create valid sessions. |
| **High** | Tokens survive assignee and trust-type changes | [survey_links.py](/home/shayman86/my-repos/FlowForm/backend/app/services/survey_links.py:62) changes a link’s assignee or type without rotating its token or distribution state. A former holder can consume it after reassignment and impersonate the new participant. |

## Medium vulnerabilities and hardening gaps

- **Invitation tokens are logged and never expire.** Raw tokens appear in API paths in [invitations.py](/home/shayman86/my-repos/FlowForm/backend/app/api/v1/account/invitations.py:57), and [request_logging.py](/home/shayman86/my-repos/FlowForm/backend/app/logging/request_logging.py:21) logs paths verbatim. No creation or redemption path enforces expiry.

- **Unverified accounts become “verified” participants.** [participants.py](/home/shayman86/my-repos/FlowForm/backend/app/services/participants.py:133) compares email strings without requiring `user.email_verified`, then upgrades the identity to verified.

- **Survey access tokens are plaintext in the core database.** A core-database read compromise yields all active respondent URLs. Store only an HMAC/SHA-256 lookup and reveal the raw value once.

- **Sensitive account actions lack step-up authentication.** A normal bearer token can request a password-change ticket, remove MFA, or delete the account through [profile.py](/home/shayman86/my-repos/FlowForm/backend/app/api/v1/account/profile.py:95).

- **Unauthenticated arbitrary-recipient email sender.** [health.py](/home/shayman86/my-repos/FlowForm/backend/app/api/v1/system/health.py:66) exposes a production-capable SES test endpoint. Worker-local limits do not prevent distributed abuse.

- **Credentialed CORS defaults to any origin.** [extensions.py](/home/shayman86/my-repos/FlowForm/backend/app/core/extensions.py:35) combines wildcard-default origins with credentials. `SameSite=Lax` limits ordinary cross-site attacks, but compromised same-site sibling origins remain dangerous.

- **Resource-exhaustion controls are weak.** There is no Flask or Caddy body-size cap. Rate limiting is per worker, trusts the first `X-Forwarded-For` value, and never evicts distinct IP keys.

- **CSV formula injection.** Survey editors can create a `question_key` beginning with `=`, `+`, `-` or `@`, which [export.py](/home/shayman86/my-repos/FlowForm/backend/app/services/admin_results/core/export.py:59) writes directly to CSV.

- **Studio is frameable.** CloudFront’s [static response policy](/home/shayman86/my-repos/FlowForm/infra/deployment/aws/cdk/flowform_infra/constructs/static_site_construct.py:82) lacks CSP `frame-ancestors` and `X-Frame-Options`, leaving authenticated actions exposed to clickjacking.

- **Auth0 access/refresh tokens, drafts and AI prompts persist locally.** [main.tsx](/home/shayman86/my-repos/FlowForm/frontend/apps/studio-app/src/main.tsx:24) uses Auth0 localStorage caching. Survey drafts and AI descriptions survive ordinary logout, increasing shared-browser and future-XSS impact. No reachable application XSS was found.

- **Cross-database operations are not durable sagas.** Response deletion commits before core deletion without compensation; session-start cleanup is best-effort and reconciliation detects only one orphan direction.

- **Infrastructure hardening gaps:** Grafana tokens are placed in `0644` environment files; dev/rehearsal Postgres traffic is plaintext; internal API/log hops use unauthenticated HTTP; the dev Flask debugger is LAN-exposed with writable code/AWS mounts; Packer can disable Proxmox TLS verification; backend/Squid/Alloy images and GitHub Actions use mutable tags; Docker build contexts can include ignored `.env` files.

- **Security observability is incomplete.** Audit-log primitives and a database table exist, but production actions do not call them. Sensitive result responses/exports also lack explicit `Cache-Control: private, no-store`.

- **AWS deployment assurance is incomplete.** The RDS stack remains a scaffold and application bootstrap is not wired, so real backup, deletion protection, TLS, IAM, retention and database encryption settings cannot be validated.

- **Current CI paths are stale.** Workflow paths reference `infra/containers/dev/...`, while current files are under `infra/containers/strategies/dev/...`. The current feature commit has no corresponding green CI run.

## Known vulnerable dependencies

The dependency scan found **12 unique advisories across 14 locked package/version matches**. I did not find a currently reachable FlowForm exploit path for these, but the versions should be upgraded.

| Locked dependency | Advisories and fix | Reachability |
|---|---|---|
| Authlib 1.7.0 | [CVE-2026-44681](https://github.com/advisories/GHSA-r95x-qfjj-fjj2), [CVE-2026-41479](https://github.com/advisories/GHSA-w8p2-r796-3vmq); upgrade to 1.7.1+ | Vulnerable authorization-server grant APIs are not used; FlowForm imports JOSE/JWT support. |
| Click 8.3.1 | [PYSEC-2026-2132 / CVE-2026-7246](https://osv.dev/vulnerability/PYSEC-2026-2132); upgrade to 8.3.3+ | Vulnerable `click.edit()` path was not found. |
| Astro 6.4.8 | [transition animation XSS](https://github.com/advisories/GHSA-4g3v-8h47-v7g6), [directive XSS](https://github.com/advisories/GHSA-7pw4-f3q4-r2p2), [attribute-name XSS](https://github.com/advisories/GHSA-f48w-9m4c-m7f5); upgrade to 7.1.0+ | Site is statically generated and current transition values are literals. |
| brace-expansion 1.1.15, 2.1.1, 5.0.6 | [CVE-2026-13149](https://github.com/advisories/GHSA-3jxr-9vmj-r5cp); upgrade each fixed branch | Build/glob tooling only. |
| fast-uri 3.1.2 | GHSA-4c8g-83qw-93j6 and GHSA-v2hh-gcrm-f6hx; upgrade to 3.1.4+ | Transitive build/schema validation. |
| js-yaml 4.2.0 | [CVE-2026-59869](https://github.com/advisories/GHSA-52cp-r559-cp3m); upgrade to 4.3.0 | Used on trusted local OpenAPI input. |
| sharp 0.34.5 | GHSA-f88m-g3jw-g9cj; upgrade to 0.35.0+ | Build-time checked-in images. |
| svgo 4.0.1 | GHSA-2p49-hgcm-8545; upgrade to 4.0.2+ | Build-time checked-in SVG input. |

The backend security job has an important false-negative: [run_backend_security.sh](/home/shayman86/my-repos/FlowForm/backend/scripts/run_backend_security.sh:42) resolves fresh loose constraints—currently Authlib 1.7.2 and Click 8.4.2—while the runtime image uses the vulnerable frozen [uv.lock](/home/shayman86/my-repos/FlowForm/backend/uv.lock:87). CI must audit the exact deployed lock/environment.

## Controls that are working

- Access tokens use Auth0 validation; ID tokens enforce RS256, JWKS signatures, issuer, audience and expiry.
- SQLAlchemy expressions are used consistently; no dynamic SQL injection sink was found.
- Response encryption uses AES-256-GCM, fresh 12-byte nonces, AAD, survey-scoped KMS context and HMAC-derived opaque locators.
- The response database does not store emails, Auth0 subjects, user IDs, survey IDs or core session IDs.
- Respondent cookies are `Secure`, `HttpOnly`, path-scoped and `SameSite=Lax`.
- Pydantic validation and generic client error responses are broadly sound.
- AWS networking uses isolated app/database subnets, no NAT, scoped security groups, IMDSv2 and private S3 origins.
- Most runtime containers use read-only filesystems, dropped capabilities and `no-new-privileges`.
- GitHub secret scanning and push protection are enabled, although Dependabot alerts/security updates are currently disabled.

## Validation and limitations

- Backend unit tests: **218 passed**.
- Bandit: **0 Medium/High findings** over 18,812 LOC; its 15 Low findings were false positives on action literals such as `issue` and `rotate`.
- Infrastructure container, image, LocalStack seed, shell syntax, Terraform-format and Packer-format validators passed.
- Dependency review queried the locked Python, frontend and CDK graphs through OSV; `pip-audit` independently reported Click.
- Docker Scout required authentication, so base-image/OS package CVEs remain unassessed.
- I did not attack a live deployment, Auth0 tenant, SES account, AWS account, Proxmox host, database, browser session or network. Live WAF/firewall/IAM/backup behavior therefore remains outside this result.

No audit-authored repository changes were made. The worktree was initially clean, but [count_lines.sh](/home/shayman86/my-repos/FlowForm/scripts/tools/count_lines.sh) became modified by another process during the audit. All audit workers denied editing it, and I left it untouched rather than overwrite an unknown user-owned change.