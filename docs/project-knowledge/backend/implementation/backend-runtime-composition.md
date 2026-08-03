---
title: Backend runtime composition
aliases: ["Backend runtime composition", "Flask application assembly", "Backend process lifecycle"]
document_type: implementation
status: verified
authority: canonical
verified_evidence_digest: sha256:a31bdd938a4f59e95a8e849dbafd8541d971cd67ed7f1587d8859b536b48273b
last_edited: 2026-08-04
tags: [backend]
related_code:
  - "../../../../backend/app/core/factory.py"
  - "../../../../backend/app/core/extensions.py"
  - "../../../../backend/app/db/manager.py"
  - "../../../../backend/app/db/session.py"
  - "../../../../backend/app/tracing/extension.py"
  - "../../../../backend/gunicorn.conf.py"
change_triggers:
  - "../../../../backend/app/core/"
  - "../../../../backend/app/db/"
  - "../../../../backend/app/aws/"
  - "../../../../backend/app/cache/"
  - "../../../../backend/app/email_service/"
  - "../../../../backend/app/logging/"
  - "../../../../backend/app/tracing/"
  - "../../../../backend/gunicorn.conf.py"
related_docs: ["Backend knowledge", "Backend code organization", "Backend configuration patterns", "Telemetry and health", "Configuration and secrets"]
---

# Backend runtime composition

The backend is assembled through one Flask application factory. Typed settings
enter at startup and are attached to the application before extensions,
database sessions, routes, middleware, and development-only interfaces are
registered. Routes and services consume initialized capabilities rather than
constructing provider clients or database engines at call sites.

```text
environment and secret files
            |
            v
      validated settings
            |
            v
      application factory
       /      |       \
      v       v        v
 extensions  routes  request lifecycle
      |                  |
      v                  v
 external clients   core + response sessions
```

## Startup sequence

The durable assembly order is:

1. configure bootstrap logging and resolve validated settings;
2. create the Flask application and attach settings;
3. configure tracing and full application logging;
4. initialize shared extensions for cache, AWS clients, email, databases,
   authentication, URL converters, and CORS;
5. register per-request database-session hooks and the versioned API
   blueprints;
6. register rate limiting, normalized error handling, and development/test
   OpenAPI interfaces; and
7. ensure ORM models are registered and initialize required permission seed
   data.

Configuration and initialization failures are treated as non-recoverable boot
failures. They are logged as concise operational errors and terminate startup
instead of allowing a partially initialized application to serve requests.

## Extension ownership

Shared capabilities are application-lifecycle objects, not route globals with
independent configuration:

| Capability | Runtime ownership |
| --- | --- |
| Database manager | Owns separate core and response SQLAlchemy engines and session factories. |
| AWS client manager | Owns configured SDK clients for KMS, Secrets Manager, and SES application paths. |
| Email service manager | Assembles renderer, SES sender, and email-specific rate limiter. |
| Authentication extension | Verifies bearer credentials and exposes the resolved external subject to routes. |
| Application cache | Owns bounded process-local caches used by account, session, and cryptographic paths. |
| CORS and URL converters | Apply validated transport policy and bounded route-parameter types. |

These objects provide capability and lifecycle. They do not prove an external
provider is reachable, an email was delivered, a cache is shared between
workers, or deployed credentials grant the intended permissions. Persistent
database records and wrapped key material remain sources of truth; the
in-process caches are performance aids.

## Per-request database lifecycle

Each request opens an independent SQLAlchemy session for the core store and
another for the response store and places them in Flask's request context.
Repository and service calls receive the appropriate session explicitly. At
request teardown, an exceptional request rolls back both sessions before they
are closed.

Opening both sessions does not create a shared transaction. A service that
writes both databases must define commit order, rollback and compensation
behavior, and any later reconciliation. The concrete submission and encryption
workflow is documented in [[responses-and-encryption|Responses and
encryption]].

## Production worker lifecycle

Gunicorn preloads the application in its master process so invalid
configuration fails once before workers are created. Preloading also means
process-owned resources need an explicit fork boundary:

- inherited database connection pools are disposed after each worker forks;
- the tracing exporter provider is created in the worker rather than inherited
  from the master; and
- pending traces are flushed during worker exit.

Worker count, binding, timeouts, telemetry export, database connectivity, and
provider credentials remain deployment configuration. Repository assembly
shows how the process should behave, not that a deployed process is healthy.

## Related documents

- [[backend-index|Backend knowledge]]
- [[code-organization|Backend code organization]]
- [[backend-configuration-patterns|Backend configuration patterns]]
- [[telemetry-and-health|Telemetry and health]]
- [[configuration|Configuration and secrets]]
