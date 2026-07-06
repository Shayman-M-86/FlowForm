# Caddy on EC2 Implementation Notes

This note condenses the Caddy deployment discussion into a focused companion to
the [FlowForm Deployment Implementation Plan](core-sketch-plan.md). It expands
the Caddy-specific parts of the plan: the EC2 application stack, the production
Docker Compose runtime, Route 53 DNS-01 certificate issuance, and the locked-down
network shape.

## Decision

Run Caddy inside Docker Compose on the public EC2 application instance. Caddy is
the only public HTTP service for the backend. It terminates HTTPS, renews TLS
certificates automatically, and reverse proxies requests over the private Docker
network to the Flask/Gunicorn container.

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
EC2 instance in public subnet
  |
  v
Docker Compose
  |-- Caddy container
  |     |-- listens on public 443
  |     |-- manages ACME certificates with Route 53 DNS-01
  |     `-- reverse proxies to flask:8000
  |
  `-- Flask/Gunicorn container
        |-- no public host port
        `-- connects to RDS over the VPC
```

The EC2 instance still has a public IP because the current plan deliberately
avoids an ALB/ECS rewrite for the first staging rollout. The app container does
not need a public port. Only Caddy binds to the host. This is a cost decision,
not just a sequencing one — Caddy on the instance replaces an ALB entirely; see
[cost-model.md](../cost-model.md) for the budget behind it and the triggers
that would justify the ALB/private-subnet upgrade.

## Caddy Responsibilities

Caddy should:

- Receive public HTTPS traffic for `api.<domain>`.
- Obtain and renew certificates with DNS-01 validation through Route 53.
- Reverse proxy requests to the backend container, for example `flask:8000`.
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

The practical first version is simple:

| Resource | Public inbound | Private inbound |
|---|---:|---|
| EC2 app instance | `443` from `0.0.0.0/0` | none required |
| Caddy container | host-published `443` | Docker network to Flask |
| Flask/Gunicorn container | none | Docker network from Caddy |
| RDS Postgres | none | `5432` from EC2 security group |

Do not publish the Flask/Gunicorn port on the EC2 host. In Compose, prefer
`expose` for the backend container:

```yaml
expose:
  - "8000"
```

Do not use a host-published Flask port:

```yaml
ports:
  - "8000:8000"
```

RDS should live in private subnets. Its security group should allow Postgres only
from the EC2 application security group, matching the database-stack direction
in [Phase 1d](core-sketch-plan.md#phase-1--cdk-restructure-infra-only-nothing-deployed-to-prod-yet).

## Outbound Access

Even in the locked-down design, the EC2 host and containers need outbound access.
Security groups are not domain-name firewalls, so the first staging version can
use broad outbound HTTPS while keeping inbound strict.

Recommended initial outbound rules:

| Source | Destination | Port | Why |
|---|---|---:|---|
| EC2 / Caddy | Internet HTTPS | `443` | ACME provider and Route 53 API |
| EC2 / containers | DNS resolver | `53` | Resolve AWS and ACME endpoints |
| EC2 / Flask | RDS security group | `5432` | App database connections |
| EC2 | AWS APIs | `443` | ECR pull, Secrets Manager, SSM, CloudWatch |

A later hardening pass can replace some public AWS API access with VPC endpoints
where it is worth the added complexity.

## IAM Boundary

The EC2 instance profile should grant only what the runtime needs:

- Route 53 hosted-zone-scoped record changes for DNS-01 validation.
- Read access to environment-specific Secrets Manager secrets and SSM
  parameters.
- ECR image pull permissions for the backend and custom Caddy images.
- SSM Session Manager access, avoiding SSH keys.
- CloudWatch logging permissions if Docker logs are shipped there.

This lines up with [Phase 1c](core-sketch-plan.md#phase-1--cdk-restructure-infra-only-nothing-deployed-to-prod-yet)
and the deploy mechanism in [Phase 2c](core-sketch-plan.md#phase-2--backend-runtime-on-ec2).

## Compose and Caddyfile Sketch

The production Compose file belongs under `infra/docker/`, as called out in
[Phase 2a](core-sketch-plan.md#phase-2--backend-runtime-on-ec2). It should have
two services at first: Caddy and Flask/Gunicorn. RDS is external.

```yaml
services:
  caddy:
    image: <account>.dkr.ecr.<region>.amazonaws.com/flowform-caddy:<tag>
    ports:
      - "443:443"
    volumes:
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - flask

  flask:
    image: <account>.dkr.ecr.<region>.amazonaws.com/flowform-backend:<tag>
    expose:
      - "8000"
    env_file:
      - /opt/flowform/backend.env

volumes:
  caddy_data:
  caddy_config:
```

```caddyfile
api.flow-form.com.au {
    tls {
        dns route53
    }

    reverse_proxy flask:8000
}
```

Keep Caddy's `/data` volume persistent so certificate state survives container
replacement.

## Staging Validation Checklist

Validate this in staging before adding prod:

- `api.<staging-domain>` resolves to the EC2 Elastic IP.
- EC2 security group allows public `443` and does not allow public `8000` or
  `5432`.
- RDS security group allows `5432` only from the EC2 app security group.
- Caddy obtains a certificate with Route 53 DNS-01.
- Certificate renewal can reach Route 53 and the ACME provider from the
  container.
- The Caddy container can access instance-role credentials through IMDS, or the
  chosen alternative credential path is documented.
- `curl https://api.<staging-domain>/...` reaches the backend through Caddy.
- `curl http://<ec2-ip>:8000` fails from the public internet.
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
