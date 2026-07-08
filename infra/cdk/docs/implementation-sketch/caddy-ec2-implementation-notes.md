# Caddy on EC2 Implementation Notes

This note condenses the Caddy deployment discussion into a focused companion to
the [FlowForm Deployment Implementation Plan](core-sketch-plan.md). It expands
the Caddy-specific parts of the plan: the EC2 application stack, the production
Docker Compose runtime, Route 53 DNS-01 certificate issuance, and the locked-down
network shape.

Two deeper companions cover the implementation detail:
[docker-hardening.md](docker-hardening.md) (Compose files, Caddyfile/Squid
config, container constraints, proxy env plumbing) and
[host-hardening.md](host-hardening.md) (Linux access paths, IMDSv2, host
firewalls, patching, logging). Use
[ec2-compose-due-diligence-checklist.md](ec2-compose-due-diligence-checklist.md)
as the staging-readiness checklist for the host/network/IAM pieces that Compose
does not prove by itself.

## Decision

Run Caddy inside Docker Compose on the public EC2 application instance. Caddy is
the only public HTTP service for the backend. It terminates HTTPS, renews TLS
certificates automatically, and reverse proxies requests over the private VPC
to the Flask/Gunicorn container on the app instance.

This matches the main deployment plan's target backend architecture:
Route 53 -> EC2 -> Docker Compose -> Caddy + Gunicorn -> RDS. See
[Target architecture](core-sketch-plan.md#flowform-deployment-implementation-plan),
[Phase 1c](core-sketch-plan.md#phase-1--cdk-restructure-infra-only-nothing-deployed-to-prod-yet),
and [Phase 2](core-sketch-plan.md#phase-2--backend-runtime-on-ec2).

## Runtime Shape

```text
Internet
  |
  | HTTPS 443 only
  v
Route 53 A record: api.<domain> -> Elastic IP
  |
  v
PUBLIC proxy EC2 (public subnet)
  |-- Caddy container
  |     |-- listens on public 443 (80 for redirect)
  |     |-- manages ACME certificates with Route 53 DNS-01
  |     `-- reverse proxies to the app EC2's PRIVATE IP
  |
  `-- Squid container (outbound forward proxy, port 3128
        from the app security group only — see Egress Proxy below)
  |
  | private VPC route
  v
PRIVATE app EC2 (private subnet, no public IP, NO internet route)
  `-- Docker Compose
        `-- Flask/Gunicorn container
              |-- reachable only from the proxy security group
              |-- egress: proxy EC2 (Auth0 + AWS APIs), free S3
              |   gateway endpoint (ECR layers), RDS — nothing else
              `-- connects to RDS over the VPC
```

Two instances, split by trust: the proxy box is the only internet-facing
machine (inbound TLS termination AND allow-listed outbound), while the app
box has no public IP and no route to the internet at all. There is still no
ALB, no NAT Gateway, and no paid interface endpoints — the isolation costs
one extra small instance; see [cost-model.md](../cost-model.md) for the
budget and for why the endpoint-heavy variant of this design was rejected.

## Caddy Responsibilities

Caddy should:

- Receive public HTTPS traffic for `api.<domain>`.
- Obtain and renew certificates with DNS-01 validation through Route 53.
- Reverse proxy requests to the private app instance, for example
  `http://{$APP_PRIVATE_IP}:5000`.
- Keep Flask/Gunicorn private inside the Docker Compose network.
- Avoid storing AWS credentials in files, images, or GitHub secrets.

The main plan already calls out that stock Caddy does not include the Route 53
DNS provider. Build a small custom image with `xcaddy` and the
`caddy-dns/route53` plugin, then push it to ECR alongside the backend image. See
[Phase 2b](core-sketch-plan.md#phase-2--backend-runtime-on-ec2).

## Certificate Flow

Use DNS-01 validation rather than HTTP-01.

That means:

- Public inbound port 80 is not required for certificate issuance.
- Caddy must be able to call the ACME provider, usually Let's Encrypt or ZeroSSL.
- Caddy must be able to call the Route 53 API to create and remove temporary TXT
  validation records.
- The EC2 instance role must grant narrowly scoped Route 53 change permissions
  for the hosted zone used by `api.<domain>`.

The preferred credential path is instance-role credentials through IMDS. The
known staging risk is that the Caddy container must actually be able to reach
instance metadata. Validate the IMDSv2 container path early, including the hop
limit setting. The main plan identifies this as the most likely silent failure
in the design. See [Phase 2b](core-sketch-plan.md#phase-2--backend-runtime-on-ec2)
and [Risks / decisions](core-sketch-plan.md#risks--decisions-to-confirm-before-starting).

## Network Lockdown

Exact allowed paths — everything else denied:

| Resource | Public inbound | Private inbound |
|---|---:|---|
| Proxy EC2 (public subnet) | `80`/`443` from `0.0.0.0/0` | `3128` (Squid) from app SG only |
| App EC2 (private subnet) | none — no public IP | backend port from proxy SG only |
| RDS Postgres | none | `5432` from app SG only |

Route tables are the load-bearing control: the private app subnet has **no**
`0.0.0.0/0` route at all (no IGW, no NAT) — only local VPC routing and the
free S3 gateway endpoint. Even a compromised container has no path to the
internet except the allow-listed proxy.

Do not publish the Flask/Gunicorn port on any public interface. In the private
app Compose file, bind Gunicorn only to the app instance's private IP:

```yaml
ports:
  - "${APP_PRIVATE_IP:?}:5000:5000/tcp"
```

Do not use a broad host-published Flask port:

```yaml
ports:
  - "0.0.0.0:5000:5000"
```

RDS should live in private subnets. Its security group should allow Postgres only
from the EC2 application security group, matching the database-stack direction
in [Phase 1d](core-sketch-plan.md#phase-1--cdk-restructure-infra-only-nothing-deployed-to-prod-yet).

## Outbound Access and the Egress Proxy

Security groups are not domain-name firewalls, so domain-level egress
control lives in a forward proxy (Squid) on the proxy instance. The app
instance has no internet route; ALL of its external traffic — including
AWS API calls — goes through the proxy or fails.

| Source | Destination | Port | Why |
|---|---|---:|---|
| Proxy EC2 (Caddy) | Internet HTTPS | `443` | ACME provider and Route 53 API |
| Proxy EC2 (Squid) | allow-listed domains | `443` | Auth0, AWS service endpoints, Sentry/PostHog if used |
| App EC2 | Proxy EC2 SG | `3128` | forward proxy for all external traffic |
| App EC2 | S3 gateway endpoint | `443` | ECR image layers (free endpoint; ECR stores layers in S3) |
| App EC2 | RDS SG | `5432` | app database connections |

Squid's allow-list (CONNECT/SNI-based): the Auth0 tenant + custom domain,
and the regional AWS endpoints the app role actually uses —
`secretsmanager`, `kms`, `email` (SES v2 API — note the backend sends via
the **SESv2 API with boto3, not SMTP**), `api.ecr`, the exact account ECR
registry host, and `ssm`. No `sts`, no `*.amazonaws.com`, and no
`*.auth0.com` wholesale. Everything else is denied and logged.

**Proxy configuration on the app instance** — the part that makes or
breaks this design:

- Docker daemon (`HTTP_PROXY`/`HTTPS_PROXY` in the systemd drop-in) for
  ECR pulls; boto3/requests in the backend container via the same env
  vars in the Compose file.
- `NO_PROXY` must cover: `localhost,127.0.0.1,169.254.169.254` (IMDS —
  identity breaks without it), the VPC CIDR (RDS + S3 gateway endpoint
  traffic must NOT hairpin through the proxy), and Docker-internal
  service names.
- **Session Manager does not work through an HTTPS proxy.** Management
  path for the private box is an **EC2 Instance Connect Endpoint**
  (free) — or pay for the SSM interface-endpoint trio (~$22/month) if
  EICE proves insufficient. The proxy box itself uses SSM normally.
- Deploys to the app instance go via the chosen management path; image
  pulls work because ECR *auth* rides the proxy and *layers* ride the S3
  gateway endpoint.

The Deferred Hardening section's VPC-endpoint upgrade remains available
per service if proxying a particular AWS API becomes a recurring pain.

## IAM Boundary

Two instance profiles, split like the instances:

**Proxy EC2 role** (internet-facing box gets the DNS power, nothing else):

- Route 53 hosted-zone-scoped record changes for DNS-01 validation.
- ECR pull for the Caddy/Squid images.
- SSM Session Manager access (this box can use SSM normally).

**App EC2 role** (= the security stack's existing `task_role`):

- Read access to scope-specific Secrets Manager secrets and SSM
  parameters.
- KMS encrypt/decrypt on the scope key; SES send.
- ECR image pull permissions for the backend image.
- CloudWatch logging permissions if Docker logs are shipped there.

This lines up with [Phase 1c](core-sketch-plan.md#phase-1--cdk-restructure-infra-only-nothing-deployed-to-prod-yet)
and the deploy mechanism in [Phase 2c](core-sketch-plan.md#phase-2--backend-runtime-on-ec2).

## Secrets and Configuration Bootstrap

Decision: the backend does **not** fetch its own config from Secrets
Manager/SSM at startup (no boto3 config loader). Instead a host-side
bootstrap script — run from user data at boot and re-run by the SSM deploy
command — materialises everything the Compose stack needs, using the
instance role:

```text
Instance bootstrap (instance role, no static keys)
  ├── Secrets Manager  → /run/flowform/secrets/<NAME>.secret.txt
  │     tmpfs mount, root-owned 0600 — memory-backed, never on EBS
  └── SSM /flowform/<env>/backend/ → /opt/flowform/backend.env
        non-secret FLOWFORM_* config + DB hosts/names/users + image refs

docker compose --env-file /opt/flowform/backend.env \
  -f docker-compose.app.yml up -d
```

Why this over in-app fetching:

- **Dev/prod parity.** `backend/app/core/config.py` already loads the DB
  passwords, Flask secret key, and Auth0 Management API client secret from
  mounted files (`*_FILE` settings); dev Compose exercises the identical
  path daily. No prod-only config code.
- **Startup robustness.** Container restarts never depend on Secrets
  Manager/SSM being reachable; AWS is touched once per deploy.
- **tmpfs neutralises the "secrets on disk" objection.** The secret files
  live in memory only and disappear on reboot (bootstrap re-creates them).

The split follows the usual rule: credentials and keys in Secrets Manager
(DB app passwords, Flask secret key, Auth0 Management API client secret),
non-secret runtime config in SSM Parameter Store (Auth0 domain/audience/client
IDs, KMS key ARN, linkage secret ARN, SES from-address, logging levels, RDS
endpoints, image refs, private IPs). Compose files reference only names and
paths — see `infra/docker/docker-compose.proxy.yml` and
`infra/docker/docker-compose.app.yml`.

Note that the backend still uses the instance role at runtime for its
own AWS calls (KMS session encryption, the linkage-key secret, SES) —
that is application behaviour, not config loading. `AwsSettings` already
allows the static key fields to be absent, so boto3 can use the default
credential chain and IMDS on EC2. This means the backend container needs
IMDS access — the same IMDSv2 hop-limit ≥ 2 requirement already flagged
for Caddy in [Certificate Flow](#certificate-flow).

## Compose and Caddyfile Sketch

The production Compose files belong under `infra/docker/`, as called out in
[Phase 2a](core-sketch-plan.md#phase-2--backend-runtime-on-ec2). The proxy
instance uses `docker-compose.proxy.yml` (Caddy + Squid); the private app
instance uses `docker-compose.app.yml` (backend only). RDS is external.

```yaml
proxy EC2:
  docker compose --env-file /opt/flowform/proxy.env \
    -f docker-compose.proxy.yml up -d

app EC2:
  docker compose --env-file /opt/flowform/backend.env \
    -f docker-compose.app.yml up -d
```

```caddyfile
{$API_DOMAIN} {
    tls {
        dns route53
    }

    reverse_proxy http://{$APP_PRIVATE_IP}:5000 {
        health_uri /api/v1/system/health/ready
    }
}
```

Keep Caddy's `/data` volume persistent so certificate state survives container
replacement.

## Staging Validation Checklist

Validate this in staging before adding prod:

- `api.<staging-domain>` resolves to the EC2 Elastic IP.
- EC2 security group allows public `443` and does not allow public `5000` or
  `5432`.
- RDS security group allows `5432` only from the EC2 app security group.
- Caddy obtains a certificate with Route 53 DNS-01.
- Certificate renewal can reach Route 53 and the ACME provider from the
  container.
- The Caddy container can access instance-role credentials through IMDS, or the
  chosen alternative credential path is documented.
- `curl https://api.<staging-domain>/...` reaches the backend through Caddy.
- `curl http://<app-private-ip>:5000` fails from outside the proxy path.
- Flask/Gunicorn can connect to both FlowForm databases on RDS.
- Deployment through SSM can pull images and restart Compose without SSH.

The full staging proof also needs the broader cutover checks in
[Phase 5](core-sketch-plan.md#phase-5--cutover-and-decommission): API through
Caddy, RDS connectivity, frontend integration, Auth0 round trip, and end-to-end
form submission.

## Deferred Hardening

Keep these out of the first pass unless staging reveals a need:

- ALB in public subnets with EC2 in private subnets.
- NAT reduction through VPC endpoints and PrivateLink where supported.
- Caddy certificate-expiry monitoring.
- Docker log shipping to CloudWatch.
- SSM Patch Manager and rebuildable instance bootstrap.

These belong with the post-cutover hardening work in
[Phase 6](core-sketch-plan.md#phase-6--hardening-post-cutover-prioritized-backlog).
