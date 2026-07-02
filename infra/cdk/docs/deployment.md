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
uv run cdk synth -c env=dev        # preview the CloudFormation template
uv run cdk diff -c env=dev         # see what would change
uv run cdk deploy -c env=dev       # deploy all stacks
uv run cdk deploy -c env=dev FlowForm-Dev-Security   # deploy one stack
```

Swap `-c env=dev` for `-c env=staging` or `-c env=prod` once those accounts
are assigned (see [`environments.md`](environments.md) — currently
placeholders).

## Deploy order

`app.py` wires explicit stack dependencies: Security → Network → Database →
Application → Observability, with Amplify deployed independently (it
doesn't depend on the VPC/database/ECS chain). `cdk deploy` (no stack name)
respects this order automatically.

## Verifying a deploy

```bash
cd infra/cdk
uv run pytest              # synth-time assertions (currently: security_stack)
uv run cdk synth -c env=dev > /dev/null && echo "synth OK"
```

## Tearing down

```bash
uv run cdk destroy -c env=dev FlowForm-Dev-Observability
# ... reverse dependency order ...
uv run cdk destroy -c env=dev FlowForm-Dev-Security
```

`prod`'s KMS keys and secrets have `RemovalPolicy.RETAIN` — destroying the
prod security stack will not delete them. This is intentional; delete them
manually only if you're certain.
