# Infrastructure migration map

> TODO(migration): Replace this inventory with verified final ownership and
> remove every copied-file migration marker before cutover.

## Copied for migration

| Target area | Existing source responsibility |
| --- | --- |
| `contracts/` | Runtime parameter contract and immutable image-source catalogue |
| `containers/backend/` | Backend Docker build |
| `containers/caddy/` | Caddy build and AWS DNS-01 configuration |
| `containers/squid/` | Squid template and AWS destination policy |
| `containers/alloy/` | App and proxy Alloy configurations |
| `images/machine/` | AWS Packer source, base provisioning, bootstrap scripts, and role Compose definitions |
| `cdk/` | Python CDK application, stacks, constructs, configuration, and assertions |
| `database/` | SQL baselines, AWS bootstrap, local initialization, and fixtures |
| `operations/` | Existing AWS publication, secret seeding, database bootstrap, and AMI commands |
| `tests/infrastructure/` | Existing AWS-relevant structural and operator tests |

## Deliberately not copied

- Proxmox deployment code and Packer sources;
- rehearsal Compose overrides, fixtures, LocalStack, and TLS shims;
- generated `cdk.out` and Packer manifests;
- `.venv`, `node_modules`, caches, and editor state;
- checked-out environment files, secret files, Terraform state, and other local
  machine state;
- existing GitHub workflows, which remain active until the new tree is ready
  for one-shot cutover.

## Placeholder rule

Zero-byte files mark intended responsibilities that do not yet have a clean
implementation. They should be implemented or deliberately removed during the
wiring pass. Their presence is not evidence that the corresponding feature
works.
