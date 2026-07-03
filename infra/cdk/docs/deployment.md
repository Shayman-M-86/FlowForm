# Deployment

## Prerequisites

- AWS CLI configured with credentials for the target account
- `uv` installed
- Node.js (CDK CLI itself is a Node tool, invoked via `npx` or a global
  install — not vendored in this Python project)

## One-time bootstrap (per account/region)

```bash
cd infra/cdk
uv sync
npx aws-cdk bootstrap aws://<ACCOUNT_ID>/ap-southeast-2
```

This creates the CDK toolkit stack (S3 bucket + IAM roles CDK needs to
deploy). Run once per AWS account + region combination.

## Deploying

```bash
cd infra/cdk
npx cdk synth -c env=dev        # preview the CloudFormation template
npx cdk diff -c env=dev         # see what would change
npx cdk deploy -c env=dev       # deploy all stacks
npx cdk deploy -c env=dev FlowForm-Dev-Security   # deploy one stack
```

For `dev` this deploys a single stack (`FlowForm-Dev-Security`) — dev's
app, databases, and frontends run locally, so that's its whole AWS
footprint (see [`environments.md`](environments.md)).

Swap `-c env=dev` for `-c env=staging` or `-c env=prod` when deploying
those environments (all three share one AWS account — see
[`environments.md`](environments.md)). Note that staging/prod synth fails
early until the environment's `.env.<env>` file provides its Auth0 public
config (`AUTH0_DOMAIN` / `AUTH0_CLIENT_ID` / `AUTH0_AUDIENCE`) — this is
deliberate, so a deploy can't go out with missing Auth0 config.

## Deploy order

For full deployments (staging/prod), `app.py` wires explicit stack
dependencies: Security → Network → Database → Application →
Observability, with Amplify deployed independently (it doesn't depend on
the VPC/database/ECS chain). `cdk deploy` (no stack name) respects this
order automatically. For dev only the Security stack exists.

## Verifying a deploy

```bash
cd infra/cdk
uv run pytest              # synth-time assertions (currently: security_stack)
npx cdk synth -c env=dev > /dev/null && echo "synth OK"
```

## Tearing down

```bash
# dev has one stack:
npx cdk destroy -c env=dev FlowForm-Dev-Security

# staging/prod: reverse dependency order —
npx cdk destroy -c env=staging FlowForm-Staging-Observability
# ... then Application, Database, Amplify, Network ...
npx cdk destroy -c env=staging FlowForm-Staging-Security
```

`prod`'s KMS keys and secrets have `RemovalPolicy.RETAIN` — destroying the
prod security stack will not delete them. This is intentional; delete them
manually only if you're certain.
