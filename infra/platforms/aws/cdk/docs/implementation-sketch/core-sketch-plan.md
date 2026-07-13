# FlowForm Deployment Implementation Plan

**Target architecture:** GitHub Actions (CI/CD) → CDK (infrastructure) → S3 + CloudFront + ACM + Route 53 (frontends) / EC2 + Docker Compose + Caddy + Gunicorn (backend) → RDS Postgres. Amplify is removed.

This shape is budget-driven: single public EC2 instead of ECS/ALB, no NAT Gateway, one small RDS instance. The monthly cost target, the isolation trade-off it accepts, and the upgrade triggers are recorded in [cost-model.md](../cost-model.md).

## Phase 1 — CDK restructure (infra only, nothing deployed to prod yet)

**1a. Retire the Amplify stack.** Delete `AmplifyStack` and `amplify_app_construct.py` from the CDK app, and remove the Amplify build configs from the repo (the recent commits touching `amplify.yml` become dead weight). Don't destroy the live Amplify app yet — that happens at cutover (Phase 5).

**1b. Add a `FrontendStack` (one per env, two distributions).** For each of `studio-app` and `public-site`:

- Private S3 bucket (no static website hosting; CloudFront Origin Access Control only).
- CloudFront distribution with SPA fallback (403/404 → `/index.html`), compression, and a cache policy that long-caches hashed assets but not `index.html`.
- ACM certificate — must live in `us-east-1` even though the app region is `ap-southeast-2`; use a cross-region certificate construct or a small dedicated us-east-1 stack.
- Route 53 alias records (e.g. `app.flow-form.com.au` → public-site, `studio.flow-form.com.au` → studio-app; exact subdomains to confirm).
- Stack outputs: bucket names + distribution IDs, consumed by the deploy workflow.

**1c. Rework `ApplicationStack` from ECS/ALB to EC2.** The current stack is an ECS sketch; replace it with:

- One EC2 instance (start small, e.g. t4g/t3.small) in a public subnet with an Elastic IP, security group allowing inbound 443 (and 80 only if you want HTTP→HTTPS redirect — with DNS-01 you can keep 80 closed and do the redirect on 443-only, but opening 80 for redirects is harmless and user-friendly).
- Instance profile / IAM role granting: Route 53 change permissions **scoped to the hosted zone** (for Caddy's DNS-01), read access to the env's Secrets Manager secrets and SSM parameters, ECR pull, and SSM Session Manager (no SSH keys).
- User data or an SSM document that installs Docker + Compose and bootstraps the app stack.
- Route 53 A record for the API domain (e.g. `api.flow-form.com.au`) → Elastic IP.

See [Caddy on EC2 Implementation Notes](caddy-ec2-implementation-notes.md) for the Caddy-specific network lockdown, IAM boundary, and certificate-flow details behind this stack shape.

**1d. Rework `DatabaseStack` for RDS.** One RDS Postgres instance per env (staging can be single-AZ, prod multi-AZ later), in private subnets, security group allowing 5432 only from the EC2 security group. Master credentials in Secrets Manager via the existing KMS key. The `core` and `response` split stays as two databases (or two DB users with separate grants) on the one instance — a bootstrap/migration step creates both. Decide explicitly whether PgBouncer joins the Compose stack; with one Gunicorn service it's likely unnecessary at first — leave a slot for it rather than building it now.

**1e. Extend `SecurityStack` with CI/CD identity.** Add a GitHub OIDC provider and per-env deploy roles (no long-lived AWS keys in GitHub): an infra-deploy role (CDK deploy permissions), a frontend-deploy role (S3 sync + CloudFront invalidation on the specific bucket/distribution ARNs), and a backend-deploy role (ECR push + SSM SendCommand to the instance). Trust policies pinned to the repo and, for prod, to the `main` branch/environment.

**1f. Environments.** Keep the existing `dev = Security-only, everything local` model — it's a good cost decision. Wire `staging` fully first; add a `prod` env config once staging works end-to-end. A `FlowForm-Shared` stack is only warranted if something is genuinely cross-env (hosted zone lookup, the OIDC provider — which is account-global anyway); otherwise skip it.

## Phase 2 — Backend runtime on EC2

**2a. Production Compose file** (`infra/docker/docker-compose.prod.yml`): two services — Caddy and the Flask/Gunicorn backend (image from ECR). No Postgres container; `DATABASE_URL`s point at RDS. Secrets fetched at deploy/boot time from Secrets Manager into an env file (or entrypoint fetch), never committed.

**2b. Caddy image with Route 53 DNS-01.** Stock Caddy doesn't include the Route 53 DNS provider — you need a custom image built with `xcaddy` adding `caddy-dns/route53`. Small Dockerfile in `infra/docker/`, pushed to ECR alongside the backend image. The Caddyfile: `api.<domain>` site block, `tls { dns route53 }`, reverse proxy to the backend container. Credentials come from the instance role via IMDS — one gotcha to verify early: the container must be able to reach instance metadata (IMDSv2 hop limit ≥ 2 for containers, or pass the role via ECS-style env — test this in staging first, it's the most likely silent failure in this design). The companion [Caddy notes](caddy-ec2-implementation-notes.md#compose-and-caddyfile-sketch) include the expected Compose and Caddyfile shape.

**2c. Deploy mechanism.** GitHub Actions builds and pushes the backend image to ECR, then triggers the instance via **SSM SendCommand** (or an SSM document) to `docker compose pull && docker compose up -d`. No SSH from CI.

**2d. Migrations.** Run as an explicit pipeline step before the app swap: a one-shot container run (via the same SSM path) executing the migration command against RDS for both databases. Sequence: push image → run migrations → restart services.

## Phase 3 — Frontend build & deploy

**3a. Build-time configuration.** Each app needs per-env values (API base URL, Auth0 domain/client ID) baked in at build. Source them from SSM parameters (fetched in the workflow) or GitHub environment variables — pick one and be consistent; SSM keeps CDK as the source of truth for names.

**3b. Deploy steps per app:** build → sanity-check the output (`dist/index.html` exists, non-empty) → `aws s3 sync dist/ s3://<bucket> --delete` (upload hashed assets before `index.html` to avoid a window where the new index references missing chunks) → CloudFront invalidation of `/index.html` (or `/*` to keep it simple initially).

**3c. Cross-cutting config that changes with the move:** update backend CORS allowlist to the new CloudFront domains, and Auth0 allowed callback/logout/origin URLs for the new subdomains.

## Phase 4 — GitHub Actions pipelines

Keep [ci.yml](vscode-webview://1ivkklv2udi1n6o5t35hf5igi9oipbicioc5bipqn0rsgi3ld6up/.github/workflows/ci.yml) as the PR gate and extend it; add deploy workflows:

- **`ci.yml` (PRs + pushes)** — existing security + tests, plus: frontend lint/typecheck/test/build for both apps, and `cdk synth` + `cdk diff` (diff posted to the PR). **No deploys from PRs.**
- **`deploy.yml` (push to `main`, and `staging` for the staging env)** — job chain with `needs:` so the pipeline graph is visible: tests → `cdk deploy` → backend image build/push → migrations → backend restart via SSM → frontend builds → S3 sync + invalidation → smoke check (curl the API health endpoint and each frontend URL). Auth via OIDC roles from 1e.
- **GitHub Environments:** `staging` auto-deploys; `production` gets a required-reviewer gate so prod deploys need a manual approval click.
- Optional separate `deploy-infra.yml` with manual dispatch for infra-only changes — nice-to-have, not required initially.

See [GitHub Actions CI/CD Flow Sketch](github-actions-cicd-flow.md) for the intended PR gate, deploy workflow, OIDC credential flow, and rollback boundaries.

## Phase 5 — Cutover and decommission

1. Stand everything up in **staging** and verify the full flow: HTTPS cert issuance via DNS-01, API through Caddy, RDS connectivity, both frontends via CloudFront, Auth0 login round-trip, form submission end-to-end. Use the [Caddy staging checklist](caddy-ec2-implementation-notes.md#staging-validation-checklist) for the proxy/network-specific checks.
2. Repeat for prod behind the approval gate.
3. Flip Route 53 records for the real domains to CloudFront/EC2 (low TTL beforehand).
4. Delete the Amplify apps in the console/CDK, remove leftover Amplify config from the repo, and revoke any Amplify-related service roles.

## Phase 6 — Hardening (post-cutover, prioritized backlog)

- RDS automated backups + snapshot retention verified; a documented restore drill.
- CloudWatch: EC2/RDS alarms, Docker log shipping (awslogs driver), CloudFront + S3 access logs — fold into the existing `ObservabilityStack`.
- Caddy cert-renewal monitoring (an alarm on cert expiry beats discovering a renewal failure at day 90).
- EC2 patching via SSM Patch Manager; consider making the instance rebuildable from user-data alone so it's cattle, not a pet.
- Later escape hatch (already anticipated in the discussions): the Compose file ports cleanly to ECS/ALB if the single instance becomes the bottleneck — nothing in this design blocks that.

## Risks / decisions to confirm before starting

1. **Caddy + Route 53 in a container** needs the custom xcaddy build and IMDSv2 hop-limit fix — prove this in staging first; it's the design's main novelty. The detailed risk notes live in [Caddy certificate flow](caddy-ec2-implementation-notes.md#certificate-flow).
2. **Subdomain naming** — the summaries used `app.`/`admin.flow-form.com.au`; repo apps are `public-site`/`studio-app`. Pick final hostnames before creating certs.
3. **Existing ECS-oriented `ApplicationStack`** — the summaries chose EC2, but the CDK sketch chose ECS. This plan follows the summaries (EC2); if you'd rather keep the ECS direction the Phase 2 shape changes substantially, so flag it now if so.
4. **PgBouncer** — deferred, not included.
5. **Auth0 redirect URIs and backend CORS** must be updated in lockstep with the domain flip or logins break at cutover.

Sensible build order: 1e (OIDC roles) → 1b–1d (staging infra) → 2 (backend on staging EC2) → 3 (frontends to staging) → 4 (pipelines) → 5 (prod + cutover). Each phase leaves staging in a testable state before the next begins.
