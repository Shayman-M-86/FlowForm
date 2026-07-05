# Runbooks

Copy-pasteable commands for common operational actions against the CDK
stacks. Each file covers one area; this page is the index.

| Runbook | What it covers |
|---|---|
| [teardown.md](teardown.md) | Destroying a whole environment or individual stacks, and the order/gotchas |
| [frontend-deploy.md](frontend-deploy.md) | Building and publishing the frontends to S3 + CloudFront (manual + CI) |

All commands assume:

- You're in `infra/cdk/` (`cd infra/cdk` first).
- AWS credentials for the target account are active (`aws login` / `aws sso login` / `AWS_PROFILE`).
- The CDK CLI runs via `npx cdk …` (it's a Node tool, not vendored in this Python project).

Stack names follow `FlowForm-<Env>-<Stack>`, e.g. `FlowForm-Staging-Frontend`.
`<env>` in `-c env=<env>` is one of `dev`, `staging`, `prod`.
