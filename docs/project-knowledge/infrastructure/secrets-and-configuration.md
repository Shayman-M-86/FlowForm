---
title: Secrets and configuration
aliases: ["Secrets and configuration"]
document_type: workflow
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-28
tags: [configuration, security, infrastructure]
related_code:
  - "../../../scripts/secrets/"
  - "../../../backend/app/core/config.py"
  - "../../../backend/app/db/iam_auth.py"
  - "../../../infra/containers/strategies/dev/compose/"
  - "../../../infra/deployment/bootstrap/"
related_docs:
  - "Infrastructure knowledge"
  - "Configuration implementation"
  - "Local infrastructure"
---

# Secrets and configuration

Classify a value before delivery. The backend consumes nested environment
variables and file-backed values. Development and production require the Auth0
management secret to be configured by file and require its startup validation;
the test environment is the explicit exception.

```text
secret sources
  |-- local generated database values
  |-- authenticated remote application values
  |
  v
tmpfs runtime secret directory
  |
  v
read-only container secret mounts
  |
  v
typed backend configuration
```

## Local development secret assembly

Generate missing machine-local database passwords, then fetch persistent
development secrets into a tmpfs-backed runtime directory:

```sh
scripts/secrets/generate-secrets.sh dev
export AWS_PROFILE=flowform-dev
aws login --profile "$AWS_PROFILE"
scripts/secrets/fetch-dev-secrets.sh
export FLOWFORM_SECRET_DIR="$XDG_RUNTIME_DIR/flowform-secrets"
```

The fetch script refuses a missing or non-tmpfs `XDG_RUNTIME_DIR` and refuses a
secret destination outside it. It retrieves `app_secret_key` and
`auth0_mgmt_secret` from the non-production application secret, combines them
with the local PostgreSQL password files, validates the resulting files, and
the development Compose stack bind-mounts that directory read-only at
`/run/secrets`.

The generator creates only local dev/test values and does not overwrite an
existing file. Development database passwords are deliberately retained beside
the local volumes; replacing them without resetting those volumes breaks the
database credential relationship. The test stack can generate its app secret
and uses a direct throwaway Auth0 value rather than a persisted Auth0 secret
file.

## Runtime delivery boundary

`infra/deployment/config/runtime-parameter-contract.json` names non-secret
runtime groups and secret-resource categories. Bootstrap scripts are the
runtime consumers of parameters and secret material. App bootstrap requires an
explicit deployment target and checks its database auth modes before writing
secrets: AWS IAM mode omits database password files, while rehearsal password
mode writes and mounts them through its Compose overlay. Application and Auth0
management values remain file-backed in both strategies. The repository
contract is not proof that a particular cloud deployment has been provisioned
or that its values are current.

Under IAM mode no database credential is delivered or stored, so the backend
supplies one per connection instead. `backend/app/db/iam_auth.py` signs a
short-lived RDS authentication token locally from the instance's AWS
credentials and injects it as the connection password through SQLAlchemy's
`do_connect` hook. Because tokens expire well within an engine's lifetime, the
token is generated for each physical connection rather than embedded in the
engine URL, which leaves pooling and recycling behaviour identical across both
modes. IAM connections are made over TLS.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[configuration|Configuration implementation]]
- [[local-infrastructure|Local infrastructure]]
