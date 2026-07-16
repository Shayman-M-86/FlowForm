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

`security_stack.py` is the only fully-built stack so far; the rest are
structural stubs with `# TODO` markers — see `aws-overview.md` for status.

## Environment model

- **dev** deploys the Security stack only (KMS, secrets, SES send access).
  The app, both databases, and the frontends run locally
  (`infra/environments/development/compose/` + Vite dev servers) — no VPC, RDS, ECS, or Amplify.
- **staging** is the one shared non-prod cloud environment: full stack set,
  doubles as the integration environment.
- **prod** is the same stack set as staging with retention/protection
  turned on.
