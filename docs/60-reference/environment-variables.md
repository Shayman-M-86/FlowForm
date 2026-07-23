---
title: Environment variables
aliases:
  - "Environment variables"
document_type: reference
status: draft
authority: canonical
verified_against_commit: null
tags: [configuration]
related_code:
  - "../../backend/app/core/config.py"
  - "../../infra/deployment/bootstrap/"
  - "../../infra/containers/"
  - "../../frontend/apps/"
related_docs:
  - "Configuration catalogue"
  - "Secrets and configuration"
  - "Configuration index"
---

# Environment variables
Provides concise verified reference facts for environment variables.

## Reference scope

This page catalogues maintained environment-variable families and their owners. It deliberately omits values and does not treat example files, local secret files, Terraform state, or generated environment files as authoritative secret stores.

## Canonical source
Each variable is authoritative in the module or script that reads it; this
catalogue only points there.

- **Backend application settings** — `backend/app/core/config.py` (the settings
  model). See also [[configuration-catalogue|Configuration catalogue]].
- **Boot-time deploy variables** — the header comment blocks of the bootstrap
  scripts under `infra/deployment/bootstrap/`, which list each script's required
  and optional environment. The app bootstrap
  (`infra/deployment/bootstrap/bootstrap-app.sh`) documents, among others:
  - `BACKEND_IMAGE` — overrides the image ref (rehearsal points it at the local registry).
  - `BOOTSTRAP_DRY_RUN=1` — print intended actions, change nothing.
  - `BOOTSTRAP_IMAGE_PULL_MAX_ATTEMPTS` — image-pull retries before failing the boot (default 60).
  - `BOOTSTRAP_IMAGE_PULL_RETRY_DELAY_SECONDS` — delay between those retries (default 5).

  The pull retry lets the app boot wait out an empty rehearsal registry until the
  operator's image push lands; in production the image is already present, so the
  pull succeeds on the first attempt and the retry adds no latency.

## Entries

| Family | Representative names | Owner and behaviour |
| --- | --- | --- |
| Runtime selection | `FLOWFORM_ENV` | Required by `backend/app/core/config.py`; accepted values are `dev`, `test`, and `prod`. |
| Flask application | `FLOWFORM_APP_DEBUG`, `FLOWFORM_APP_SECRET_KEY_FILE` | `FlowForm.app` settings. Production-style Compose supplies the key through a mounted file. |
| Auth0 | `FLOWFORM_AUTH0_DOMAIN`, `FLOWFORM_AUTH0_AUDIENCE`, `FLOWFORM_AUTH0_CLIENT_ID`, `FLOWFORM_AUTH0_MGMT_ID`, `FLOWFORM_AUTH0_MGMT_SECRET`, `FLOWFORM_AUTH0_MGMT_SECRET_FILE`, `FLOWFORM_AUTH0_MGMT_DOMAIN`, `FLOWFORM_AUTH0_MGMT_VALIDATE_ON_STARTUP` | `FlowForm.auth0` settings. Dev and production require the management secret file and startup validation; only tests accept the direct throwaway secret or disabled probe. A configured file takes precedence. The canonical management domain may differ from the login custom domain. |
| Databases | `DATABASE_CORE_*`, `DATABASE_RESPONSE_*` | `Settings.database` and Compose. Each database supports a URL or host/port/name/user plus an application-password file. Core and response settings are separate families. |
| AWS and encryption | `FLOWFORM_AWS_REGION`, `FLOWFORM_ENCRYPTION_KMS_KEY_ARN`, `FLOWFORM_ENCRYPTION_LINKAGE_SECRET_ARN`, `FLOWFORM_ENCRYPTION_*CACHE*` | AWS client and response-encryption settings in `backend/app/core/config.py`. Credential resolution normally comes from the AWS SDK chain or instance role. Dev and production boot fails unless the role/credentials can read the linkage secret and complete a KMS round trip; test mode skips those calls. |
| Email | `FLOWFORM_EMAIL_FROM_ADDRESS`, `FLOWFORM_EMAIL_FROM_NAME`, `FLOWFORM_EMAIL_REPLY_TO_ADDRESS`, `FLOWFORM_EMAIL_ENABLED`, rate/cooldown settings | SES sender and application-level email limits. |
| CORS and rate limits | `FLOWFORM_CORS_ORIGINS`, `FLOWFORM_CORS_SUPPORTS_CREDENTIALS`, `FLOWFORM_RATE_LIMIT_*` | Explicit API-origin allowlist plus the existing rate-limit settings. Production requires at least one origin and rejects `*` with credentials. |
| Logging | `FLOWFORM_LOGGING_LEVEL`, `FLOWFORM_LOGGING_LOG_JSON`, `FLOWFORM_LOGGING_LOG_FILE`, `FLOWFORM_LOGGING_REQUESTS`, `FLOWFORM_LOGGING_DURATION` | Backend logging configuration. Runtime Compose expects stdout JSON and Docker-owned rotation. |
| Tracing | `FLOWFORM_TRACING_ENABLED`, `FLOWFORM_TRACING_OTLP_ENDPOINT`, `FLOWFORM_TRACING_SAMPLE_RATIO`, `FLOWFORM_TRACING_SERVICE_NAME` | Backend OpenTelemetry configuration. Tracing defaults off; deployed rehearsal settings enable export to app Alloy at `http://alloy:4317`. The sample ratio is validated from 0 through 1. |
| Studio build | `VITE_API_BASE_URL`, `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_AUDIENCE`, `VITE_AUTH0_CLIENT_ID` | Vite inputs read by the Studio application. |
| Frontend development Compose | `PUBLIC_SITE_PORT` | Optional host-port override for the public-site development container. Public-site navigation is owned by TypeScript configuration, not an environment variable. |
| Runtime Compose | `BACKEND_IMAGE`, `CADDY_IMAGE`, `SQUID_IMAGE`, `ALLOY_IMAGE`, `API_DOMAIN`, `APP_PRIVATE_IP`, `PROXY_PRIVATE_IP`, `SQUID_*`, `GRAFANA_CLOUD_LOKI_*`, `GRAFANA_CLOUD_TEMPO_*`, `OTEL_*` | Shared runtime Compose interpolation. Bootstrap-generated `/opt/flowform/*.env` files supply deployed values; every deployed image value is required and AWS values are intended to be complete private-ECR digest references. Caddy's `OTEL_*` values are set directly by Compose. |
| Bootstrap | `FLOWFORM_SCOPE`, `AWS_REGION`, `BOOTSTRAP_ENDPOINT_URL`, `FLOWFORM_SECRET_DIR`, `BOOTSTRAP_DRY_RUN`, retry settings | App, proxy, and database bootstrap scripts. `BOOTSTRAP_ENDPOINT_URL` is the rehearsal seam for LocalStack; production leaves it unset. |

Pydantic settings use `_` as the nested delimiter with a maximum of two splits, so `FLOWFORM_LOGGING_LEVEL` maps to `flowform.logging.level` and `DATABASE_CORE_HOST` maps to `database.core.host`.

## Update procedure

Search direct environment reads, Pydantic setting fields, Compose interpolation, and bootstrap header contracts. Record names and ownership only; never copy values from local `.env`, state, cache, or secret files into documentation.

## Related documents

- [[configuration-catalogue|Configuration catalogue]]
- [[secrets-and-configuration|Secrets and configuration]]
- [[configuration-index|Configuration index]]
