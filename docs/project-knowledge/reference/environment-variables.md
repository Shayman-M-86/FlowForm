---
title: Environment variables
aliases: ["Environment variables"]
document_type: reference
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-27
tags: [configuration]
related_code: ["../../../backend/app/core/config.py", "../../../infra/deployment/bootstrap/", "../../../infra/containers/", "../../../frontend/apps/"]
related_docs: ["Configuration catalogue", "Secrets and configuration", "Configuration index"]
---

# Environment variables

This reference catalogs variable families and their readers. It deliberately
omits values: local secret files, Terraform state, examples, and generated
environment files are not authoritative secret stores.

| Family | Representative names | Owner |
| --- | --- | --- |
| Runtime selection | `FLOWFORM_ENV` | Backend settings model |
| Application/Auth0 | `FLOWFORM_APP_*`, `FLOWFORM_AUTH0_*` | Backend settings model |
| Databases | `DATABASE_CORE_*`, `DATABASE_RESPONSE_*` | Backend settings and Compose |
| AWS/encryption | `FLOWFORM_AWS_*`, `FLOWFORM_ENCRYPTION_*` | Backend settings and AWS clients |
| Email/CORS/rate limits | `FLOWFORM_EMAIL_*`, `FLOWFORM_CORS_*`, `FLOWFORM_RATE_LIMIT_*` | Backend settings |
| Logging/tracing | `FLOWFORM_LOGGING_*`, `FLOWFORM_TRACING_*` | Backend logging/tracing configuration |
| Studio build | `VITE_API_BASE_URL`, `VITE_AUTH0_*` | Studio application build configuration |
| Runtime images/network | `BACKEND_IMAGE`, `CADDY_IMAGE`, `API_DOMAIN`, private-IP and proxy variables | Runtime Compose/bootstrap |
| Bootstrap | `FLOWFORM_SCOPE`, `AWS_REGION`, `BOOTSTRAP_*`, `FLOWFORM_SECRET_DIR` | Bootstrap script headers |

Each name is authoritative only in the module or script that reads it. Confirm
the exact spelling, defaults, requiredness, and security behaviour in that
reader before use. Never document a value from local configuration.

## Related documents

- [[configuration-catalogue|Configuration catalogue]]
- [[secrets-and-configuration|Secrets and configuration]]
- [[configuration-index|Configuration index]]
