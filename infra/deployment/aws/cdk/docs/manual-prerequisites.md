# Manual Prerequisites

Everything CDK assumes already exists — the hand-done steps that must
happen before (or right after) a deploy, and why each one isn't in code.
Three categories:

- **Permanent** — deliberately never in CDK.
- **Deferred** — manual today, planned to move into CDK later.
- **One-time setup** — done once per account/environment, then forgotten.

## Permanent — never in CDK

### Domain registration + Route 53 hosted zone

The `flow-form.com.au` registration and its hosted zone are hand-made and
stay that way. Creating a hosted zone assigns it four AWS nameservers, and
the domain registration must point at them — so if CDK ever recreated the
zone (stack rename, accidental destroy), DNS would silently break until
the registrar was updated by hand anyway. The zone is a singleton with no
config to drift; CDK only imports it (`HostedZone.from_lookup`). Records
*inside* the zone (ALB aliases, CloudFront aliases, DKIM) are fair game
for CDK.

### SES production access (sandbox exit)

Every AWS account starts in the SES sandbox (can only email verified
addresses). Exiting requires a request to AWS support with a use-case
description — no IaC tool can do this. Already done for the current
account; repeat if the project ever moves/splits accounts.

### GitHub Actions deploys (no stored AWS keys)

Frontend deploys run from `.github/workflows/deploy.yml`, which assumes
the CDK-created `flowform-<env>-frontend-deploy` role via GitHub's OIDC
provider — nothing to set up in GitHub, and no AWS keys in GitHub
secrets. The OIDC identity provider itself is created by **staging's**
Security stack (it's an account-level singleton), so prod's Security
stack deploys after staging's.

Historical note: the retired Amplify Hosting approach needed a GitHub PAT
in Secrets Manager (`flowform/shared/github-pat`). Nothing CDK-managed
uses it anymore — it can be deleted once the hand-made Amplify app is
retired too.

### Prod apex cutover from the hand-made Amplify app

The apex DNS records for `flow-form.com.au` currently point at the
original hand-made public-site Amplify app. Before the first **prod**
deploy of the Frontend stack, remove that app's domain association
(Amplify console → old app → Domain management → remove) so the CDK
Route 53 aliases can claim the apex for CloudFront. Staging's hostnames
are unclaimed, so staging needs no cutover.

### Auth0 tenant + applications

Auth0 is external to AWS and stays manually configured (revisit Auth0
Deploy CLI / Terraform only if tenant config needs to be reproducible).

Already done for the tenant: a **custom domain** (`auth.flow-form.com.au`)
fronts the login flow — the frontend's `VITE_AUTH0_DOMAIN` points at it,
not at the raw `dev-....au.auth0.com` tenant domain. Its verification
CNAME lives as a hand-made record in the Route 53 hosted zone; CDK must
leave it alone.

The backend needs **both** domains because Auth0 does not serve the
Management API (`/api/v2`) on custom domains — a token request there fails
with `access_denied: Service not enabled within domain`. So per env, set
two backend SSM params under `/flowform/<scope>/backend/`:

- `FLOWFORM_AUTH0_DOMAIN` → the **custom** domain (`auth.flow-form.com.au`),
  so token `iss` validation matches the frontend's tokens.
- `FLOWFORM_AUTH0_MGMT_DOMAIN` → the **canonical** tenant
  (`dev-....au.auth0.com`), used only by the Management API client. If
  omitted, the mgmt client falls back to `FLOWFORM_AUTH0_DOMAIN` (correct
  only for tenants without a custom domain).

The egress allow-list (`infra/containers/strategies/aws/services/squid/allowed-domains.txt`) must admit
both hosts for the same reason.

Per environment, before its first frontend deploy:

1. Create the environment's Auth0 application (SPA/PKCE) and API audience.
2. Set callback/logout URLs for that environment's hostnames.
3. Put `AUTH0_DOMAIN` / `AUTH0_CLIENT_ID` / `AUTH0_AUDIENCE` in the
   gitignored `infra/deployment/aws/cdk/.env.<env>` file — staging/prod synth **fails
   early** until this is done.
4. Put the Management API client secret into the environment's
   `app-secrets` entry (see secret seeding below).

Staging currently bootstraps by **reusing the dev Auth0 application**
(`.env.staging` carries the same client ID/audience) — split it into its
own application + audience before real staging traffic, so tokens can't
be replayed across environments.

## Deferred — manual today, CDK later

### SES domain identity

The domain-verified SES identity for `flow-form.com.au` was hand-created
and is only imported by reference (`ses_construct.py`). Unlike the hosted
zone, this *should* eventually be CDK-managed: `ses.EmailIdentity` can
create the identity and write its DKIM records into the hosted zone
automatically, which is what makes a fresh AWS account bootstrap without
console work. It needs a small **shared stack** (the identity is
account-wide; all envs share one account, so no per-env stack can own it)
and a `cdk import` migration to adopt the existing identity without
recreating it. Do this when next touching email infrastructure
(configuration sets, bounce handling, staging setup).

### Legacy dev KMS key + linkage secret

`infra/env/dev/.backend.env` still points at the hand-created KMS key and
linkage secret. One-time cutover after the first `cdk deploy -c env=dev`
— see the steps in
[`secrets-and-config.md`](secrets-and-config.md#resolved-existing-dev-kms-key--secret--create-fresh).
After that, this item disappears.

## One-time setup

### AWS credentials

Deploys need a principal that can assume the CDK bootstrap roles
(effectively admin on the account). Any standard mechanism works
(`AWS_PROFILE`, `aws configure`, SSO). Synth also needs credentials
**once**: `HostedZone.from_lookup` makes a real Route 53 call, cached in
`cdk.context.json` afterward — commit that file and later synths (CI,
tests) are credential-free.

### CDK bootstrap

Once per account+region: `npx aws-cdk bootstrap
aws://908123139858/ap-southeast-2`. See
[`deployment.md`](deployment.md).

### Secret seeding

CDK creates the Secrets Manager entries with **generated placeholder
values only** — real values never pass through CDK or git. After the
first deploy of an environment's Security stack, seed them:
`infra/deployment/aws/scripts/seed-secrets.sh --env <env> --send` (values come from a
gitignored `.env.<env>`; see `.env.dev.example` and
[`secrets-and-config.md`](secrets-and-config.md)).
