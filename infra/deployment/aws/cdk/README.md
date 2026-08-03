# FlowForm AWS infrastructure definitions

This package declares FlowForm's AWS topology with Python CDK. It owns cloud
resource definitions and synth-time assertions; the repository-wide AWS
operations layer owns routine deployment, artifact publication, host
convergence, and recovery workflows.

Start with the [CDK operator and maintenance index](docs/README.md). Durable
architecture and operational ideas belong in FlowForm Project Knowledge rather
than in this package.

## Local setup

```bash
uv sync --extra dev
npm ci
```

## Fast validation

```bash
uv run ruff check .
../../../../scripts/tools/typecheck.sh cdk
uv run pytest -q
npx --no-install cdk synth -c env=staging
```

These checks validate source and synthesized templates. They do not prove that
an AWS environment is deployed, healthy, or recoverable.

## Package shape

```text
flowform_infra/
  config/       environment declarations and shared policy
  constructs/   reusable CDK building blocks
  stacks/       independently deployable ownership boundaries
tests/          synth-time assertions
docs/           local operator and maintenance guidance
```

Use source and synthesized output for the current resource inventory. Do not
maintain a parallel Markdown list of stacks, parameters, or resource names.
