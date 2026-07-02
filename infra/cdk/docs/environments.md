# Environments

Defined in [`infra/cdk/flowform_infra/config/environments.py`](../flowform_infra/config/environments.py).

| Env | Account | Removal policy | Deletion protection | DB instance |
|---|---|---|---|---|
| `dev` | `908123139858` | Destroy | Off | `db.t4g.micro` |
| `staging` | *TODO — not yet assigned* | Destroy | Off | `db.t4g.small` |
| `prod` | *TODO — not yet assigned* | Retain | On | `db.t4g.medium` |

`dev`'s account ID matches the one already visible in the KMS key / Secrets
Manager ARNs the backend currently uses locally
(`infra/docker/.backend.env`).

**Open decision:** whether staging/prod should live in the same AWS account
as dev, or in separate accounts (common for blast-radius isolation —
a mistake in staging can't touch prod resources). Resolve this before
assigning real account IDs and deploying either environment.

## Selecting an environment

```bash
cd infra/cdk
uv run cdk synth -c env=dev       # or staging / prod
uv run cdk deploy -c env=dev
```

Defaults to `dev` if `-c env=` is omitted (see `cdk.json` context and
`app.py`).

## Removal policy behavior

- `dev` / `staging`: KMS keys, secrets, and (once built) RDS instances are
  destroyed on `cdk destroy` — fine for throwaway environments.
- `prod`: KMS keys and secrets are retained even if the stack is destroyed;
  RDS has deletion protection enabled. This is intentional — production
  data and encryption keys should never be removable by a single
  `cdk destroy` command.
