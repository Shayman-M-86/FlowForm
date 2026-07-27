---
title: Configuration implementation
aliases: ["Configuration implementation"]
document_type: implementation
status: verified
authority: canonical
verified_evidence_digest: sha256:c4e18e6f60c3cf2eaa16332ef93756aa8da9eb3a0546d83ea87c1bebb7684256
tags: [configuration, infrastructure]
related_code:
  - "../../../backend/app/core/config.py"
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

The model accepts a complete database URL or the required database parts. A
database password file is loaded when a direct password is absent. Application
and Auth0 management settings likewise load configured secret files. In dev
and prod the Auth0 management secret file is mandatory and validation must be
enabled; production also rejects empty CORS origins and wildcard origins when
credentials are enabled.

`backend/app/aws/client_extension.py` creates KMS, Secrets Manager, and SES
clients before registering them with Flask. Startup validation is skipped in
test mode; otherwise it reads the configured linkage secret and performs an
ephemeral KMS encrypt/decrypt round trip. It raises an initialization error on
failure.

## Infrastructure contract

`runtime-parameter-contract.json` defines scope parameters, named backend and
proxy runtime groups, and the app, database, linkage, and observability secret
resource categories. It supplies names for deployment consumers rather than
storing their confidential values. Bootstrap scripts and Compose assets map the
resulting parameters and secret files to runtime processes.

Local ignored environment files, secret files, Packer variable files, and
Terraform state are runtime or generated inputs, not the canonical model. Some
can contain confidential material and should be handled accordingly.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[secrets-and-configuration|Secrets and configuration]]
- [[local-infrastructure|Local infrastructure]]
