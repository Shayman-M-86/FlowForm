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
  - "../../backend/app/aws/startup_validation.py"
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
  frontend `VITE_*` value as confidential. Bootstrap parses secret JSON from
  stdin and writes only mode-`0600` files under its tmpfs secret directory.

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
   or real Auth0 management secret. `FLOWFORM_ENV=test` also skips the AWS
   startup probes. CI generates and masks its throwaway value before starting
   Compose.
5. In the shared-host model, CDK owns scoped `app-secrets`, `db-secrets`, and
   `linkage-secret` resources plus SSM parameters. App, proxy, and database
   bootstrap materialize secret files into `/run/flowform/secrets` tmpfs while
   keeping non-secret runtime settings in root-owned env files. Compose config
   is validated before pull/up and startup waits for container health.
6. In the Proxmox rehearsal, use the `rehearsal sync` subcommand to reconcile
   the root-only PVE-host bundle plus deploy-time Auth0 and
   Grafana inputs into LocalStack. Use `rehearsal rotate
   app|database|linkage` for supported rotations and consumer convergence.
   The repository does not yet attach bootstrap to CDK-created EC2 instances or
   provide complete cloud rotation/release orchestration.

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
  Dev and production require the Auth0 Management API secret to come from
  `FLOWFORM_AUTH0_MGMT_SECRET_FILE`; only the test environment accepts the
  direct throwaway `FLOWFORM_AUTH0_MGMT_SECRET` value. When both are present
  outside tests, the mounted file takes precedence. Dev and production also
  require Auth0 management startup validation to remain enabled.
- During each dev or production backend process boot, initialization requests
  an Auth0 Management API token, reads the configured linkage secret's
  `AWSCURRENT` version, and performs a KMS encrypt/decrypt round trip with the
  configured key. Failure of any probe raises a fatal initialization error and
  prevents the process from serving requests. The KMS probe uses a random
  ephemeral value and does not persist application data; SES is not probed
  because proving send access would create an external side effect.
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
