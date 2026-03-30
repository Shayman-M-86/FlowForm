# Docker Secrets & Environment Setup

Minimal setup for local development.

---

## 1. Docker Secrets (required)

Create these files:

```text
infra/docker/secrets/FF_PGDB_INIT__PASSWORD.secret.txt
infra/docker/secrets/FF_PGDB_CORE__APP_PASSWORD.secret.txt
infra/docker/secrets/FF_PGDB_RESPONSE__APP_PASSWORD.secret.txt
```

Each file contains only the password value.

**Used for:**

- Postgres admin (init user)
- Core DB app user
- Response DB app user

---

## 2. Compose Environment Variables

Add these to your `.env` (or compose env source):

```env
# Init
FF_PGDB_INIT__USER=flowform-admin
FF_PGDB_INIT__DB=init-postgres

# Core DB
FF_PGDB_CORE_COMPOSE__HOST=postgres-core
FF_PGDB_CORE_COMPOSE__PORT=5432
FF_PGDB_CORE_COMPOSE__PUBLISHED_PORT=5432

# Response DB
FF_PGDB_RESPONSE_COMPOSE__HOST=postgres-response
FF_PGDB_RESPONSE_COMPOSE__PORT=5432
FF_PGDB_RESPONSE_COMPOSE__PUBLISHED_PORT=5433

# DB names
FF_PGDB_CORE__DB_NAME=flowform_core
FF_PGDB_RESPONSE__DB_NAME=flowform_response

# App users
FF_PGDB_CORE__APP_USER=flowform_core_app
FF_PGDB_RESPONSE__APP_USER=flowform_response_app

# Schema
FF_PGDB_CORE__SCHEMA_FILE=schema/flowform_core_db_schema_v3.sql
FF_PGDB_RESPONSE__SCHEMA_FILE=schema/flowform_response_db_schema_v3.sql
```

---

## 3. Backend `.backend.env`

Required for the backend container:

```env
FF_ENV=dev

FF_APP__DEBUG=true
FF_APP__SECRET_KEY=replace-me

# Auth0 (optional for local)
FF_AUTH0__DOMAIN=your-domain.au.auth0.com
FF_AUTH0__AUDIENCE=https://api.flowform.local

# Logging
FF_LOGGING__LEVEL=DEBUG
FF_LOGGING__LOG_JSON=false
FF_LOGGING__LOG_FILE=logs/app.log

# DB connections
FF_PGDB_CORE__HOST=postgres-core
FF_PGDB_CORE__PORT=5432
FF_PGDB_CORE__NAME=flowform_core

FF_PGDB_RESPONSE__HOST=postgres-response
FF_PGDB_RESPONSE__PORT=5432
FF_PGDB_RESPONSE__NAME=flowform_response
```

---

## 4. Key Rules

- **Never store passwords in env files** → use Docker secrets
- **Service names = hostnames** (`postgres-core`, `postgres-response`)
- Ports:
  - Core → `5432`
  - Response → `5433`

---

## 5. Quick Checklist

- [ ] Secrets files created
- [ ] `.env` variables set
- [ ] `.backend.env` configured
- [ ] Schema paths valid

Then run:

```bash
docker compose up -d --build
```
