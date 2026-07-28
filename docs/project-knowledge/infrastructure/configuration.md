---
title: Configuration implementation
aliases: ["Configuration implementation"]
document_type: implementation
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-28
tags: [configuration, infrastructure]
related_code:
  - "../../../backend/app/core/config.py"
  - "../../../backend/app/db/iam_auth.py"
  - "../../../backend/app/db/manager.py"
  - "../../../backend/app/aws/startup_validation.py"
  - "../../../infra/deployment/config/runtime-parameter-contract.json"
  - "../../../infra/deployment/bootstrap/"
related_docs:
  - "Infrastructure knowledge"
  - "Secrets and configuration"
  - "Local infrastructure"
---

# Configuration implementation

`backend/app/core/config.py` owns the typed backend settings model. It reads
environment variables using Pydantic's underscore nesting, requires
`FLOWFORM_ENV` to be `dev`, `test`, or `prod`, and turns Pydantic failures into
the application's configuration error.

```text
environment variables + secret files
                  |
                  v
         typed settings model
                  |
        validation and defaults
                  |
                  v
        application + AWS clients
                  |
                  v
           runtime services
```

## Settings and secret files

The model accepts a complete database URL or the required database parts.
Application and Auth0 management settings load configured secret files. In dev
and prod the Auth0 management secret file is mandatory and validation must be
enabled; production also rejects empty CORS origins and wildcard origins when
credentials are enabled.

Each database target selects its own authentication mode. `password` is the
default and loads a database password file when a direct password is absent.
`iam` carries no stored credential: the required parts exclude a password, and
the assembled URL omits it. The two databases are configured independently, and
the mode is not derived from `FLOWFORM_ENV`, so a deployment chooses it
explicitly. Supplying a password, a password file, or a complete URL alongside
`iam` is rejected, because either would otherwise silently take precedence over
the token path.

`backend/app/aws/client_extension.py` creates KMS, Secrets Manager, and SES
clients before registering them with Flask. Startup validation is skipped in
test mode; otherwise it reads the configured linkage secret and performs an
ephemeral KMS encrypt/decrypt round trip. It raises an initialization error on
failure.

## Infrastructure contract

`runtime-parameter-contract.json` defines scope parameters, named backend and
proxy runtime groups, and the app, database, linkage, and observability secret
resource categories. The backend runtime group includes the core and response
database auth modes. It supplies names for deployment consumers rather than
storing their confidential values. App bootstrap validates those modes against
its explicit AWS or rehearsal deployment target. AWS delivers passwordless IAM
database configuration; the rehearsal Compose overlay supplies database
password files.

Local ignored environment files, secret files, Packer variable files, and
Terraform state are runtime or generated inputs, not the canonical model. Some
can contain confidential material and should be handled accordingly.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[secrets-and-configuration|Secrets and configuration]]
- [[local-infrastructure|Local infrastructure]]
