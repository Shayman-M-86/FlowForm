# Teardown

Destroying environments and individual stacks. Read the gotchas at the
bottom before running anything against `prod`.

`FrontendCert` lives in **us-east-1** (CloudFront requires it); every other
stack is in `ap-southeast-2`. `cdk destroy` targets a stack by name and
figures out the region itself, so you don't pass region flags.

## Staging scope

Staging runs the proxy, app and PostgreSQL on Proxmox. Its AWS stacks provide
the frontend, container registry, runtime parameters and workload identity.
The [hybrid runbook](../../../../hybrid/README.md) covers the Proxmox side.
`cdk destroy --all` also selects the Security stack shared with dev. Use
explicit stack names when retiring a subset of AWS services.

## Tear down individual stacks

Destroy a single stack by name. CDK refuses if another *live* stack still
depends on it, so work from the top of the dependency chain down.

```bash
# Just the frontend hosting (buckets + CloudFront + Route 53 aliases):
npx cdk destroy -c env=staging FlowForm-Staging-Frontend

# The frontend cert (us-east-1). Destroy Frontend FIRST — it uses the cert:
npx cdk destroy -c env=staging FlowForm-Staging-FrontendCert
```

To take down just the frontend hosting entirely (e.g. to rebuild it), that
pair is the whole footprint — `Frontend` then `FrontendCert`:

```bash
npx cdk destroy -c env=staging FlowForm-Staging-Frontend FlowForm-Staging-FrontendCert
```

`FlowForm-Nonprod-Security` is the foundation — everything (dev AND
staging) depends on it, so it destroys **last**. Destroying it also
removes the GitHub OIDC provider and the `flowform-staging-frontend-deploy`
role, which breaks CI deploys until the stack is recreated.

## After a Frontend teardown: clean Route 53?

`cdk destroy FlowForm-Staging-Frontend` removes the Route 53 **alias
records** it created (they're CDK-owned). Nothing else lingers in the
hosted zone. If you ever see leftover `_<hash>.<domain>` CNAMEs, those are
ACM DNS-validation records — CDK removes them when the cert stack is
destroyed, but a mid-deploy failure can orphan them; delete by hand via
`aws route53 change-resource-record-sets` if so.

## Gotchas

- **prod retains data.** `prod`'s KMS key and Secrets Manager secrets use
  `RemovalPolicy.RETAIN`, so destroying `FlowForm-Prod-Security` leaves
  them in place (by design — losing the KMS key means losing access to
  everything it encrypted). Delete them by hand only when you're certain.
  staging/dev use `DESTROY`, so their key/secrets go with the stack.

- **S3 buckets auto-empty on staging/dev, not prod.** The frontend buckets
  are created with `auto_delete_objects` tied to the removal policy, so on
  staging/dev `cdk destroy` empties and removes them cleanly. On prod
  (RETAIN) the buckets and their objects stay.

- **Destroy `Frontend` before `FrontendCert`.** The distributions reference
  the cert; CloudFormation won't delete an in-use ACM certificate. `--all`
  handles this ordering for you.

- **CloudFront is slow to delete.** Disabling + removing a distribution
  takes several minutes; a `Frontend` destroy can sit for 5–15 min. That's
  normal, not a hang.

- **Credentials must be valid.** `cdk destroy` needs live credentials for
  the account, same as deploy. An expired session fails with
  `NoCredentials` — re-auth (`aws login`) and re-run.
