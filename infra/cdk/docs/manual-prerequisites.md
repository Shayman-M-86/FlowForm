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
*inside* the zone (ALB aliases, Amplify domains, DKIM) are fair game for
CDK.

### SES production access (sandbox exit)

Every AWS account starts in the SES sandbox (can only email verified
addresses). Exiting requires a request to AWS support with a use-case
description — no IaC tool can do this. Already done for the current
account; repeat if the project ever moves/splits accounts.

### Amplify ↔ GitHub: the PAT secret

The repo connection is CDK-managed via the GitHub App flow (the Amplify
GitHub App is already installed on `Shayman-M-86/FlowForm` — that's how
the original hand-made app connects). CDK supplies a GitHub personal
access token from Secrets Manager at app creation; afterwards webhooks
and repo access run through the installed GitHub App, not the token.

One-time setup before the first staging/prod Amplify deploy:

1. Create a GitHub PAT (classic, `repo` + `admin:repo_hook` scopes — Amplify
   needs `admin:repo_hook` to list/create the repo's webhooks, `repo` alone
   fails with "Resource not accessible by personal access token") at
   github.com/settings/tokens.
2. Store it: `aws secretsmanager create-secret --name
   flowform/shared/github-pat --secret-string '<token>'`

Keep the secret around — CloudFormation re-reads it on stack updates that
touch the Amplify apps, so refresh it in Secrets Manager when the PAT
expires. If the GitHub App ever needs (re)installing:
github.com/apps/aws-amplify-ap-southeast-2.

### Prod apex cutover from the hand-made Amplify app

A hostname can only be attached to one Amplify app at a time, and
`flow-form.com.au` currently belongs to the original hand-made public-site
Amplify app. Before the first **prod** deploy of the CDK Amplify stack,
detach the domain from the old app (Amplify console → old app → Domain
management → remove), then deploy — Amplify re-creates the DNS records
pointing at the new app. Staging's hostnames are unclaimed, so staging
needs no cutover.

### Auth0 tenant + applications

Auth0 is external to AWS and stays manually configured (revisit Auth0
Deploy CLI / Terraform only if tenant config needs to be reproducible).

Already done for the tenant: a **custom domain** (`auth.flow-form.com.au`)
fronts the login flow — the frontend's `VITE_AUTH0_DOMAIN` points at it,
not at the raw `dev-....au.auth0.com` tenant domain. Its verification
CNAME lives as a hand-made record in the Route 53 hosted zone; CDK must
leave it alone.

Per environment, before its first Amplify deploy:

1. Create the environment's Auth0 application (SPA/PKCE) and API audience.
2. Set callback/logout URLs for that environment's hostnames.
3. Put `AUTH0_DOMAIN` / `AUTH0_CLIENT_ID` / `AUTH0_AUDIENCE` in the
   gitignored `infra/cdk/.env.<env>` file — staging/prod synth **fails
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

`infra/docker/.backend.env` still points at the hand-created KMS key and
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
`scripts/seed-secrets.sh --env <env> --send` (values come from a
gitignored `.env.<env>`; see `.env.dev.example` and
[`secrets-and-config.md`](secrets-and-config.md)).
