---
title: Backend configuration patterns
aliases:
  - "Backend configuration patterns"
document_type: implementation
status: draft
authority: canonical
verified_against_commit: cd9bd50
tags: [backend, configuration]
related_code:
  - "../../../backend/app/core/config.py"
  - "../../../backend/app/core/factory.py"
  - "../../../backend/app/aws/startup_validation.py"
  - "../../../infra/env/"
  - "../../../scripts/secrets/"
related_docs:
  - "Backend implementation guides"
  - "Configuration implementation"
  - "Secrets and configuration"
  - "Testing workflow"
---

# Backend configuration patterns

Explains the backend configuration backbone in `backend/app/core/config.py`.
Use this guide when introducing a setting or secret, rather than putting new
environment reads directly into routes or services.

## Backbone and lifecycle

`Settings` is the root `pydantic-settings` model. It uses nested environment
keys (`env_nested_delimiter="_"`). The root model has separate `flowform` and
`database` branches: for example, `settings.database.core.host` is supplied as
`DATABASE_CORE_HOST`, while `settings.flowform.auth0.domain` is supplied as
`FLOWFORM_AUTH0_DOMAIN`. `get_settings()` builds and caches that typed model;
the Flask factory resolves it once, applies it to Flask, and passes it to
initialization that requires configuration.

```text
environment variables / mounted secret files
             -> Settings and nested models
             -> create_app(settings=...)
             -> Flask extensions and runtime services
```

The existing nested groups include database, Auth0, application, encryption,
AWS, email, server, logging, tracing, and rate-limiting settings. Keep a new
setting in the group that owns its concern; create another nested model only
when it represents a stable runtime responsibility.

## Adding a non-secret setting

1. Add a typed field with a safe default, or make it required when no safe
   runtime default exists, to the owning Pydantic model in `config.py`.
2. Add a model validator when fields must be mutually consistent. Validation
   should fail during settings construction rather than later in a request.
3. Thread the typed settings object through the factory/extension boundary;
   do not call `os.environ` at feature call sites.
4. Add or update a representative local environment example and the relevant
   configuration reference when the setting is user-configurable.
5. Test the accepted configuration, missing/invalid cases, and test-mode
   behaviour where applicable.

Illustrative shape:

```python
class FeatureSettings(BaseModel):
    enabled: bool = False
    timeout_seconds: int = Field(default=5, ge=1)

class FlowForm(BaseModel):
    feature: FeatureSettings

class Settings(BaseSettings):
    flowform: FlowForm
```

Use the actual naming and root model conventions in `config.py` when applying
this; the snippet only shows the relationship between a nested concern and its
validated fields.

## Secrets and startup checks

The configuration model already supports secret-file loading for database
passwords and Auth0 management credentials. Prefer a mounted secret file for a
secret runtime value rather than a tracked environment file or ad-hoc plaintext
read. `SecretStr` prevents ordinary model representation from exposing values.

Some settings carry runtime proof obligations: the AWS initialization path can
verify Secrets Manager access and a KMS round trip, while test mode skips live
provider probes. Treat a new external dependency similarly: decide explicitly
whether it is configuration-only, validated at startup, or exercised only by an
opt-in live test.

## Do not use configuration as a dumping ground

Configuration is appropriate for deployment-selected values, credentials,
endpoints, limits, and feature/runtime switches. Per-request input, database
state, and product policy that varies by project or survey belong in their own
API, domain, or persistence models instead.

## Related documents

- [[40-implementation/backend/README|Backend implementation guides]]
- [[configuration|Configuration implementation]]
- [[secrets-and-configuration|Secrets and configuration]]
- [[testing|Testing workflow]]
