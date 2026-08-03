# CDK deployment

Use this page for the CDK-specific preview and deployment boundary. Artifact
publication, release promotion, host convergence, and live verification are
separate operations.

## Validate and synthesize

From the CDK package directory:

```bash
uv run ruff check .
../../../../scripts/tools/typecheck.sh cdk
uv run pytest -q
npx --no-install cdk synth -c env=staging
```

Select the intended environment explicitly for live work. Source owns which
stacks exist for that environment and how they depend on one another.

## Preview a stack

Use the repository operation wrapper so the diff, transcript, and operation
metadata are handled consistently:

```bash
../operations/stacks/deploy.sh \
  --environment staging \
  --stack FlowForm-Staging-Network \
  --diff-only
```

Replace the example with an exact current stack name. The wrapper validates the
environment and stack shape before invoking CDK.

## Deploy a stack

After reviewing the diff:

```bash
../operations/stacks/deploy.sh \
  --environment staging \
  --stack FlowForm-Staging-Network
```

Dependencies are included unless the selected specialized operation explicitly
uses an exclusive deployment. Do not bypass the operations layer merely to
avoid a failed safety check.

## Completion boundary

A successful cloud deployment proves only that the control plane accepted the
declared transition. It does not prove that hosts converged, application
dependencies are reachable, public behaviour works, telemetry arrived, or the
environment can be recovered.

Continue with the owning artifact, host, and verification operations. The
durable lifecycle is described in
[Release recovery and readiness](../../../../../docs/project-knowledge/operations/release-recovery-and-readiness.md).

## Teardown

Teardown is a deliberate destructive workflow, not an application rollback.
Use the [teardown runbook](runbooks/teardown.md) only after resolving retained
state, shared foundations, external dependencies, and recovery consequences.
