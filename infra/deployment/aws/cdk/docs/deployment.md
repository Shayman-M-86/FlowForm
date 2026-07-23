# Deployment

## Prerequisites

- AWS CLI configured with credentials for the target account
- `uv` installed
- Node.js (CDK CLI itself is a Node tool, invoked via `npx` or a global
  install — not vendored in this Python project)

## One-time bootstrap (per account/region)

```bash
cd infra/deployment/aws/cdk
uv sync
npx aws-cdk bootstrap aws://<ACCOUNT_ID>/ap-southeast-2
```

This creates the CDK toolkit stack (S3 bucket + IAM roles CDK needs to
deploy). Run once per AWS account + region combination.

## Deploying

```bash
cd infra/deployment/aws/cdk
npx cdk synth -c env=dev        # preview the CloudFormation template
npx cdk diff -c env=dev         # see what would change
npx cdk deploy -c env=dev       # deploy all stacks
npx cdk deploy -c env=dev FlowForm-Nonprod-Security   # deploy one stack
```

For `dev` this deploys a single stack (`FlowForm-Nonprod-Security`) —
dev's app, databases, and frontends run locally, so that's its whole AWS
footprint (see [`environments.md`](environments.md)). The Security stack
is shared with staging (the `nonprod` security scope: one KMS key, one
secret set, one app role for both simulation envs), so deploying it from
either env context updates the same stack.

Swap `-c env=dev` for `-c env=staging` or `-c env=prod` when deploying
those environments (all three share one AWS account — see
[`environments.md`](environments.md)). Note that staging/prod synth fails
early until the environment's `.env.<env>` file provides its Auth0 public
config (`AUTH0_DOMAIN` / `AUTH0_CLIENT_ID` / `AUTH0_AUDIENCE`) — this is
deliberate, so a deploy can't go out with missing Auth0 config.

## Deploy order

For full deployments (staging/prod), `app.py` wires explicit stack
dependencies: Security → Registry; Security + Network → Database; and
Security + Registry + Network + Database → Application → Observability.
FrontendCert → Frontend, and Frontend also depends on Security for its deploy
role. `cdk deploy` (no stack name) respects this order automatically. Note
`FrontendCert` lives in **us-east-1** (a CloudFront requirement) while
everything else is in `ap-southeast-2`; CDK handles the cross-region wiring.
For dev only the Security stack exists.

## Verifying a deploy

```bash
cd infra/deployment/aws/cdk
uv run pytest              # synth-time assertions (currently: security_stack)
npx cdk synth -c env=dev > /dev/null && echo "synth OK"
```

## Tearing down

See [`runbooks/teardown.md`](runbooks/teardown.md) for the full teardown
runbook (whole-environment vs individual stacks, ordering, and the
prod-retention / CloudFront / us-east-1 gotchas). Quick version:

```bash
npx cdk destroy -c env=staging --all     # whole environment
npx cdk destroy -c env=dev FlowForm-Nonprod-Security   # shared with staging — see teardown.md
```
