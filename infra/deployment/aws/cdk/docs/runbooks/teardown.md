# CDK teardown

Teardown removes declared infrastructure. It is not the normal rollback for an
application release, configuration change, or database migration.

## Before continuing

Resolve all of these questions before invoking a destructive command:

- Is the target environment disposable, or does it contain retained data or
  key material?
- Does it share account-level or non-production foundations with another
  environment?
- Which resources deliberately survive stack deletion?
- Are external DNS, identity, email, or source-control integrations left
  pointing at the removed environment?
- Is there a tested restoration or recreation path?
- Has the current synthesized stack set been reviewed rather than copied from
  an older inventory?

## Preview

Use current CDK source and the cloud control plane to inspect the selected
environment. Review stack dependencies, termination protection, retention
policies, and replacements before choosing a destroy scope.

```bash
npx --no-install cdk list -c env=staging
npx --no-install cdk diff -c env=staging
```

## Destroy

For an explicitly disposable environment, CDK can select the current stack set
and respect its dependency graph:

```bash
npx --no-install cdk destroy -c env=staging --all
```

The command is intentionally interactive. Do not add non-interactive approval
flags during investigation or copy this example to production without a
separate retained-state review.

## Verify the outcome

After deletion, inspect the cloud control plane and external integrations.
Confirm which retained resources remain, whether public names still resolve,
whether automation roles still exist, and whether future reconstruction has
the required account foundation and external contracts.

Record unexpected survivors or deletions as operational evidence. Update this
runbook only when the durable teardown boundary or invocation changes; source
owns the current stack inventory.
