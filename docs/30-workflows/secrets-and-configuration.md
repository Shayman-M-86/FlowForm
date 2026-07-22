---
title: Secrets and configuration
aliases:
  - "Secrets and configuration"
document_type: workflow
status: draft
authority: canonical
verified_against_commit: null
tags: [configuration, security]
related_code:
  - "../../backend/app/core/config.py"
  - "../../scripts/secrets/"
  - "../../infra/deployment/config/runtime-parameter-contract.json"
  - "../../infra/deployment/bootstrap/"
  - "../../infra/deployment/aws/cdk/flowform_infra/stacks/security_stack.py"
related_docs:
  - "Local development"
  - "Configuration implementation"
  - "Configuration catalogue"
  - "Environment variables"
  - "Security model"
---

# Secrets and configuration

Describes how a setting or secret moves from its owning definition into local,
test, and shared-host runtime configuration. It distinguishes configuration
that may appear in environment files or SSM from credentials that must arrive
through file-backed secret mounts.

## Trigger

Use this workflow when adding or changing a backend setting, rotating local
throwaway credentials, refreshing developer secrets after reboot/login expiry,
or changing the SSM/Secrets Manager contract used by bootstrap. A new value is
not complete until every environment that consumes it has a delivery path and a
failure test.

## Preconditions

- Classify the value first. Auth0 client IDs/domains/audiences and frontend API
  URLs are public build configuration; application keys, management secrets,
  database passwords, and linkage material are secrets.
- Backend variables follow the nested Pydantic model in
  `backend/app/core/config.py`. Required configuration is validated at process
  startup, and file-backed values must exist before settings load.
- Local persistent AWS values require an active `flowform-dev` AWS login and a
  tmpfs `XDG_RUNTIME_DIR`. Shared-host bootstrap requires its instance role,
  scope, region, host addresses, and existing SSM/Secrets Manager resources.
- Do not print secret contents, commit generated secret files, or treat a
  frontend `VITE_*` value as confidential. The current dev and app bootstrap
  helpers pass complete secret JSON through a short-lived Python process
  argument; removing that process-list exposure remains an implementation gap.

## Ordered steps

1. Add or change the typed setting and its consumer. Update the relevant
   Compose environment/file mount and the shared runtime parameter contract if
   host bootstrap must deliver it.
2. For local dev, generate only machine-local PostgreSQL passwords when missing:

   ```bash
   scripts/secrets/generate-secrets.sh dev
   ```

   Existing files are skipped. The generator deliberately cannot create
   production secrets or the persistent dev Flask/Auth0 values.
3. Fetch the persistent dev values from `flowform/nonprod/app-secrets` and
   assemble the complete read-only Compose directory in tmpfs:

   ```bash
   export AWS_PROFILE=flowform-dev
   aws login --profile "$AWS_PROFILE"
   scripts/secrets/fetch-dev-secrets.sh
   export FLOWFORM_SECRET_DIR="${XDG_RUNTIME_DIR}/flowform-secrets"
   ```

4. For tests, generate per-run database and Flask values. Test Compose overrides
   inherited management settings with a dummy identity, a direct throwaway
   Auth0 secret, and startup validation disabled; it does not mount a persisted
   or real Auth0 management secret. CI generates and masks its throwaway value
   before starting Compose.
5. In the shared-host model, CDK owns scoped `app-secrets`, `db-secrets`, and
   `linkage-secret` resources plus SSM parameters. App bootstrap
   materializes four secret files into `/run/flowform/secrets` tmpfs, renders
   `/opt/flowform/backend.env` from `/flowform/<scope>/backend/*`, validates a
   backend image, and starts Compose. Proxy bootstrap renders its scoped SSM
   path into `/opt/flowform/proxy.env`; that path currently includes
   `GRAFANA_CLOUD_TOKEN`, so the resulting file must be treated as sensitive
   even though the value is stored as an SSM parameter rather than a Secrets
   Manager secret.
6. Re-run bootstrap after a supported secret/config rotation so files and env
   are re-materialized before containers restart. The repository does not yet
   attach this bootstrap to CDK-created EC2 instances or provide a complete
   cloud rotation/release orchestration.

## Inputs and outputs

Local inputs are gitignored generated env files, AWS Secrets Manager JSON, and
machine-local generated passwords. Outputs are gitignored password files paired
with local DB volumes and a root/user-private tmpfs directory mounted read-only
at `/run/secrets`. Shared-host outputs are root-owned env files plus mode `0600`
tmpfs secrets; linkage material remains in Secrets Manager and is fetched by
the backend through its ARN.

## Failure behaviour

- Settings validation raises a configuration error for missing environment,
  database parts, secret files, or required Auth0/encryption/email values.
- The dev fetch script refuses a disk-backed or out-of-scope destination and
  aborts if AWS returns an empty/missing JSON key. Re-run it after tmpfs is
  cleared; do not regenerate database passwords while their old volumes remain.
- Generators never overwrite an existing secret. Rotation requires an explicit
  replacement plan; local DB password rotation also requires a volume reset.
- `scripts/secrets/generate-env-files.sh` is not a complete renderer for the
  current dev configuration: its allowlists omit several required
  Auth0, encryption, email, logging, and AWS fields and it replaces the target
  split files. It also does not create the aggregate gitignored
  `infra/env/dev/.env` consumed by current Compose commands. Do not use it as a
  general fresh-checkout bootstrap at this baseline.
- Bootstrap fails closed on absent SSM paths, secret keys, image refs, mounts,
  or Compose failures. A dry run validates declared inputs and planned actions,
  but does not contact/prove every live dependency.

## Verification commands

Use structural checks without displaying values:

```bash
bash -n scripts/secrets/fetch-dev-secrets.sh
bash -n infra/deployment/bootstrap/bootstrap-app.sh
bash -n infra/deployment/bootstrap/bootstrap-proxy.sh
python3 scripts/secrets/generate_secrets.py --help
bash infra/tests/containers/test-container-invariants.sh
bash infra/tests/deployment/test-localstack-seed.sh
docker compose --env-file infra/env/dev/.env -f infra/containers/strategies/dev/compose/compose.yml config --quiet
```

After a real refresh, verify only file existence, ownership, mode, service
health, and the expected secret-store version identifiers. Do not include raw
values in logs or review output.

## Related documents

- [[local-development|Local development]]
- [[configuration|Configuration implementation]]
- [[configuration-catalogue|Configuration catalogue]]
- [[environment-variables|Environment variables]]
- [[security-model|Security model]]
