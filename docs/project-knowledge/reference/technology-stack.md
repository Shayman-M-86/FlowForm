---
title: Technology stack
aliases: ["Technology stack", "Tech stack"]
document_type: reference
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-28
tags: [backend, frontend, infrastructure, tooling]
related_code:
  - "../../../backend/pyproject.toml"
  - "../../../frontend/package.json"
  - "../../../frontend/apps/public-site/package.json"
  - "../../../frontend/apps/studio-app/package.json"
  - "../../../frontend/packages/"
  - "../../../infra/deployment/aws/cdk/pyproject.toml"
  - "../../../infra/deployment/proxmox/terraform/versions.tf"
  - "../../../infra/images/packer/plugins.pkr.hcl"
  - "../../../infra/containers/"
  - "../../../.github/workflows/"
  - "../../../tools/mcp/pyproject.toml"
related_docs:
  - "Reference documentation"
  - "Repository map"
  - "Frontend implementation"
  - "Deployment model"
---

# Technology stack

Inventory of every technology FlowForm depends on, grouped by area. Versions are
the constraints declared in the manifests, not resolved lockfile versions. The
manifests listed under `related_code` remain the source of truth.

## Backend

### Runtime and framework

| Technology | Constraint | Role |
| --- | --- | --- |
| Python | `>=3.14` | Language runtime |
| Flask | `>=3.1.3` | Web framework |
| Gunicorn | `>=25.1.0` | WSGI application server |
| Flask-CORS | `>=6.0.2` | Cross-origin policy |
| Click | `>=8.3.3` | CLI commands (pinned above Flask's transitive floor) |

### Data and persistence

| Technology | Constraint | Role |
| --- | --- | --- |
| PostgreSQL | `17` (image) | Primary datastore |
| SQLAlchemy | via Flask-Migrate | ORM and query layer |
| sqlalchemy-utils | `>=0.42.1` | Extra column types and helpers |
| psycopg (binary) | `>=3.3.3` | PostgreSQL driver |
| Flask-Migrate / Alembic | `>=4.1.0` | Schema migrations |
| Mako | `>=1.3.12` | Migration templating |

### Validation and configuration

| Technology | Constraint | Role |
| --- | --- | --- |
| Pydantic | `>=2.12.5` | Models and validation |
| pydantic-settings | `>=2.14.2` | Typed settings loading |
| python-dotenv | `>=1.2.2` | Local env file loading |
| email-validator | `>=2.3.0` | Email address validation |

### Identity and cryptography

| Technology | Constraint | Role |
| --- | --- | --- |
| Auth0 | — | Identity provider |
| auth0-api-python | `>=1.0.0b7` | API token verification |
| Authlib | `>=1.7.1` | OAuth/OIDC client support |
| joserfc | `>=1.6.8` | JWT/JOSE handling |
| cryptography | `>=48.0.1` | Encryption primitives |

### API contract

| Technology | Constraint | Role |
| --- | --- | --- |
| apispec | `>=6.6.1` | OpenAPI spec generation |
| OpenAPI | `backend/openapi.yaml` | Generated backend/frontend contract |

### AWS integration

| Technology | Constraint | Role |
| --- | --- | --- |
| boto3 (with `[crt]`) | `>=1.38.0` | AWS SDK |
| botocore CRT auth | — | `aws login` profile credentials in dev |
| boto3-stubs (`kms`, `rds`, `secretsmanager`) | `>=1.43.36` | Typed AWS clients |
| mypy-boto3-sesv2 | `>=1.43.18` | Typed SES v2 client |

### Observability

| Technology | Constraint | Role |
| --- | --- | --- |
| OpenTelemetry SDK | `>=1.39.1` | Tracing and metrics |
| OTLP gRPC exporter | `>=1.39.1` | Signal export |
| OTel instrumentation: Flask | `>=0.60b1` | Request spans |
| OTel instrumentation: SQLAlchemy | `>=0.60b1` | Query spans |
| OTel instrumentation: requests | `>=0.60b1` | Outbound HTTP spans |
| OTel instrumentation: botocore | `>=0.60b1` | AWS call spans |
| OTel instrumentation: logging | `>=0.60b1` | Trace-correlated logs |

### Supporting libraries

| Technology | Constraint | Role |
| --- | --- | --- |
| requests | `>=2.33.0` | HTTP client |
| urllib3 | `>=2.7.0` | HTTP transport |
| idna | `>=3.16` | International domain handling |
| cachetools | `>=5.5,<6` | In-process caching |

### Backend tooling

| Technology | Constraint | Role |
| --- | --- | --- |
| uv | — | Dependency and env management |
| Ruff | `>=0.12.0` | Lint and format (line length 120, target `py314`) |
| Pyright | `>=1.1.408` | Static type checking |
| pytest | `>=9.0.3` | Test runner |
| pytest-cov / coverage | `>=6.2.1` / `>=7.10.0` | Coverage |
| PyYAML | `>=6.0.2` | Fixture and config parsing |
| Pygments | `>=2.20.0` | Test output formatting |

## Frontend

### Workspace and build

| Technology | Constraint | Role |
| --- | --- | --- |
| pnpm | `10.24.0` | Package manager and workspaces |
| Node.js | `>=22.12.0` | Runtime |
| TypeScript | `^5.0.0` root, `~6.0.2` Studio | Language |
| Vite | `^8.1.0` | Build tool and dev server |

### Public site (`apps/public-site`)

| Technology | Constraint | Role |
| --- | --- | --- |
| Astro | `^7.1.0` | Static site framework |
| @astrojs/react | `^5.0.7` | React island integration |
| @astrojs/sitemap | `^3.7.2` | Sitemap generation |
| React / React DOM | `^19.2.7` | Interactive components |
| react-router-dom | `^7.18.1` | Client routing in islands |
| @lucide/astro | `^1.25.0` | Icons in Astro components |
| micromorph | `^0.4.5` | View transitions |

### Studio (`apps/studio-app`)

| Technology | Constraint | Role |
| --- | --- | --- |
| React / React DOM | `^19.2.7` | Application UI |
| @vitejs/plugin-react | `^6.0.1` | React build integration |
| @tanstack/react-router | `^1.121.2` | Routing (file-based, generated) |
| @tanstack/router-plugin / router-cli | `^1.121.2` / `1.121.2` | Route generation |
| @tanstack/react-query | `^5.80.2` | Server state and caching |
| @tanstack/query-persist-client-core | `^5.100.14` | Persisted query cache |
| @tanstack/react-query-devtools | `^5.80.2` | Query debugging |
| @tanstack/router-devtools | `^1.121.2` | Route debugging |
| @auth0/auth0-react | `^2.16.1` | Authentication |
| react-hook-form | `^7.56.4` | Form state |
| @hookform/resolvers | `^5.2.2` | Schema-backed validation |
| Zod | `^3.25.28` | Runtime schemas |
| openapi-fetch | `^0.17.0` | Typed API client |
| openapi-react-query | `^0.5.4` | Typed query hooks |
| react-router-dom | `^7.18.1` | Shared component routing |

### Shared packages (`packages/`)

| Package | Role |
| --- | --- |
| `@flowform/builder` | Survey authoring and form-filler surfaces |
| `@flowform/schema` | Generated contracts and Zod schemas |
| `@flowform/ui` | Shared component library |
| `@flowform/styles` | Design tokens and component CSS |
| `@flowform/site-shell` | Shared header/shell primitives |

### Styling and UI primitives

| Technology | Constraint | Role |
| --- | --- | --- |
| Tailwind CSS | `^4.2.4` | Styling |
| @tailwindcss/vite | `^4.2.4` | Tailwind build integration |
| @base-ui/react | `^1.4.1` | Headless UI primitives |
| radix-ui | `^1.4.3` | Headless UI primitives |
| class-variance-authority | `^0.7.1` | Variant-driven class composition |
| tailwind-merge | `^3.5.0` / `^3.6.0` | Class conflict resolution |
| lucide-react | `^1.14.0` | Icons |

### Code generation

| Technology | Constraint | Role |
| --- | --- | --- |
| openapi-typescript | `^7.13.0` | Types from `backend/openapi.yaml` |
| @redocly/cli | `2.34.0` | OpenAPI linting and bundling |
| js-yaml | `4.3.0` | Spec parsing in generators |
| TanStack Router CLI | `1.121.2` | Generated route tree |

### Frontend tooling

| Technology | Constraint | Role |
| --- | --- | --- |
| ESLint | `^10.0.1` | Linting |
| typescript-eslint | `^8.58.0` / `^8.60.0` | TypeScript lint rules |
| eslint-plugin-astro | `^1.7.0` | Astro lint rules |
| eslint-plugin-react-hooks | `^7.0.1` | Hook rules |
| eslint-plugin-react-refresh | `^0.5.2` | Fast-refresh rules |
| globals | `^17.4.0` / `^17.6.0` | Lint environment globals |
| Vitest | `^4.1.7` | Studio test runner |
| @vitest/ui | `^4.1.7` | Test UI |
| jsdom | `^29.1.1` | DOM test environment |
| @pinegrow/piny-vite, piny-astro | `^1.0.10`, `^1.0.8` | Visual editing integration |

## Infrastructure

### Containers

| Technology | Version | Role |
| --- | --- | --- |
| Docker / Docker Compose | — | Local, runtime, and rehearsal composition |
| BuildKit (`dockerfile:1`) | — | Image builds |
| `python:3.14.6-slim-trixie` | digest-pinned | Backend image base |
| `postgres:17` | — | Database service |
| `caddy:2-alpine` | — | Dev reverse proxy |
| `caddy:2.11.4-alpine` | digest-pinned | AWS reverse proxy base |
| `caddy:2.11.4-builder-alpine` | digest-pinned | xcaddy build stage |
| `registry:2` | — | Rehearsal image registry |
| `localstack/localstack:3` | — | Rehearsal AWS emulation |

### Edge and network services

| Technology | Version | Role |
| --- | --- | --- |
| Caddy | `2.11.4` | Reverse proxy and TLS |
| xcaddy | — | Custom Caddy builds |
| caddy-dns/route53 | `v1.6.2` | DNS-01 certificate issuance |
| Squid | — | Egress proxy |

### AWS (CDK)

| Technology | Constraint | Role |
| --- | --- | --- |
| AWS CDK (Python) | `aws-cdk-lib>=2.170.0` | Infrastructure as code |
| constructs | `>=10.4.2` | CDK construct base |
| aws-cdk CLI | `^2.1132.1` | Synth and deploy |
| hatchling | — | CDK package build backend |

Provisioned AWS services, by stack and construct:

| Service | Where |
| --- | --- |
| EC2 / VPC | `network_stack.py`, `application_stack.py` |
| RDS | `database_stack.py` |
| ECR | `registry_stack.py` |
| S3 | `static_site_construct.py` |
| CloudFront | `frontend_stack.py` |
| Certificate Manager | `frontend_cert_stack.py` |
| Route 53 | `frontend_stack.py`, Caddy DNS-01 |
| KMS | `kms_construct.py` |
| Secrets Manager | `secrets_construct.py` |
| SES | `ses_construct.py` |
| IAM | `security_stack.py` |
| SSM Parameter Store | bootstrap configuration |
| CloudWatch Logs / metrics | `observability_stack.py` |

### Machine images and virtualization

| Technology | Constraint | Role |
| --- | --- | --- |
| Packer | `>=1.10.0` | Golden image builds |
| Packer Amazon plugin | `>=1.3.3` | AMI builds |
| Packer Proxmox plugin | `>=1.1.8` | VM template builds |
| Terraform | `>=1.6.0` | Rehearsal VM provisioning |
| bpg/proxmox provider | `0.80.0` | Proxmox API |
| Proxmox VE | — | Rehearsal hypervisor |
| Amazon Linux 2023 | — | VM and AMI base OS |

### Observability pipeline

| Technology | Role |
| --- | --- |
| Grafana Alloy | Log and trace collection agent |
| Grafana Cloud Loki | Log storage (`loki.write`) |
| Grafana Cloud Tempo | Trace storage (OTLP/gRPC) |
| systemd journal | Host log source |
| Docker log source | Container log source |

## CI/CD and repository tooling

### GitHub Actions

| Workflow | Purpose |
| --- | --- |
| `ci.yml` | Lint, type check, and test |
| `deploy.yml` | Environment deployment |
| `publish-staging-images.yml` | Staging image publication |

| Action | Version |
| --- | --- |
| actions/checkout | `v4` |
| actions/setup-node | `v4` |
| actions/upload-artifact | `v4` |
| actions/github-script | `v7` |
| astral-sh/setup-uv | `v5` |
| pnpm/action-setup | `v4` |
| aws-actions/configure-aws-credentials | `v4` |
| docker/setup-buildx-action | `v3` |
| docker/build-push-action | `v7` |
| dorny/paths-filter | `v4` |

### Developer tooling

| Technology | Constraint | Role |
| --- | --- | --- |
| Git hooks (`.githooks/`) | — | Pre-commit documentation checks |
| Docsys | — | Documentation verification and evidence |
| FastMCP | `>=3.3.1` | Dev MCP server (`tools/mcp/`) |
| httpx | `>=0.27.0` | MCP server HTTP client |
| MCP | `>=1.28.1` | Model Context Protocol |
| Starlette | `>=1.3.1` | MCP server transport |
| PyJWT | `>=2.13.0` | MCP auth |
| Bash / zsh scripts | — | Repository automation (`scripts/`) |
| Claude Code / Codex agents | `.claude/`, `.codex/`, `.agents/` | Agent configuration |

## Related documents

- [[reference-index|Reference documentation]]
- [[repository-map|Repository map]]
- [[frontend-index|Frontend implementation]]
- [[deployment-model|Deployment model]]
