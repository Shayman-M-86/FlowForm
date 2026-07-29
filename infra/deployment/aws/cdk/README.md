# FlowForm Infrastructure (CDK)

AWS infrastructure for FlowForm, managed as code. See
[`docs/`](docs/) for the full picture:

- [`aws-overview.md`](docs/aws-overview.md) — what exists and why
- [`environments.md`](docs/environments.md) — dev/staging/prod
- [`secrets-and-config.md`](docs/secrets-and-config.md) — Secrets Manager vs SSM vs local `.env`
- [`deployment.md`](docs/deployment.md) — bootstrap, deploy, teardown
- [`manual-prerequisites.md`](docs/manual-prerequisites.md) — everything hand-done that CDK assumes exists
- [`runbooks/`](docs/runbooks/) — copy-pasteable commands for common actions (teardown, frontend deploy)

## Quick start

```bash
uv sync
npx cdk synth -c env=dev
```

## Layout

```text
flowform_infra/
  config/environments.py   # per-env account/region/sizing
  stacks/                  # one file per CloudFormation stack
  constructs/              # reusable pieces shared across stacks
tests/                     # synth-time assertions (aws_cdk.assertions)
```

Security, Registry, Network, Database, Application, and frontend hosting have
substantive resources. Observability remains a structural boundary. See
`aws-overview.md` for the current stack map.

The app and proxy consume distinct role AMIs published through
`/flowform/<environment>/ec2/appAmiId` and `proxyAmiId`. Both descend from the
shared base built under `infra/machine-images/definitions/`, but CDK never
launches that base directly. Each instance requests a 10 GiB encrypted gp3
root volume, which cannot be smaller than its role AMI snapshot.

## Environment model

- **dev** deploys the Security stack only (KMS, secrets, SES send access).
  The app, both databases, and the frontends run locally
  (`infra/containers/runtime/development/compose/` + Vite dev servers) — no
  VPC, RDS, ECS, or Amplify.
- **staging** is the one shared non-prod cloud environment: full stack set,
  doubles as the integration environment.
- **prod** is the same stack set as staging with retention/protection
  turned on.
