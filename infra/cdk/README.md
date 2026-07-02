# FlowForm Infrastructure (CDK)

AWS infrastructure for FlowForm, managed as code. See
[`docs/`](docs/) for the full picture:

- [`aws-overview.md`](docs/aws-overview.md) — what exists and why
- [`environments.md`](docs/environments.md) — dev/staging/prod
- [`secrets-and-config.md`](docs/secrets-and-config.md) — Secrets Manager vs SSM vs local `.env`
- [`deployment.md`](docs/deployment.md) — bootstrap, deploy, teardown

## Quick start

```bash
uv sync
uv run cdk synth -c env=dev
```

## Layout

```
flowform_infra/
  config/environments.py   # per-env account/region/sizing
  stacks/                  # one file per CloudFormation stack
  constructs/              # reusable pieces shared across stacks
tests/                     # synth-time assertions (aws_cdk.assertions)
```

`security_stack.py` is the only fully-built stack so far; the rest are
structural stubs with `# TODO` markers — see `aws-overview.md` for status.
