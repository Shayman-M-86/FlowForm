---
title: Secrets and configuration
aliases: ["Secrets and configuration"]
document_type: workflow
status: verified
authority: canonical
verified_evidence_digest: sha256:2cfb51ed43b55b203122afc9a88117ae12034b33e7bfdda40bdc832b6153d8c4
last_edited: 2026-07-27
tags: [configuration, security, infrastructure]
related_code:
  - "../../../scripts/secrets/"
  - "../../../backend/app/core/config.py"
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
runtime consumers of parameters and secret material; backend settings load
database, application, and Auth0 management values from configured secret
files. The repository contract is not proof that a particular cloud deployment
has been provisioned or that its values are current.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[configuration|Configuration implementation]]
- [[local-infrastructure|Local infrastructure]]
