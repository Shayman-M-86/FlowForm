# CDK runbooks

Runbooks contain bounded operator procedures whose commands and destructive
effects must remain aligned with the current implementation.

| Runbook | Purpose |
| --- | --- |
| [Frontend deploy](frontend-deploy.md) | Manually reproduce the frontend publication path when automation needs diagnosis. |
| [Teardown](teardown.md) | Deliberately remove CDK-managed environment topology after reviewing retained and shared state. |

For ordinary stack deployment, artifact publication, release promotion, and
host convergence, use the [AWS operations index](../../../operations/README.md).
If a runbook becomes a design discussion or implementation plan, move its
durable ideas into Project Knowledge and route the unfinished work to
Development Workspace.
