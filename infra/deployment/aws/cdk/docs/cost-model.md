# Cost Model

This doc records **why the deployment architecture looks the way it does**:
it is the cheapest setup that still resembles a proper production deployment.
The stack shape in [aws-overview.md](aws-overview.md) and the
[deployment plan](implementation-sketch/core-sketch-plan.md) are downstream
of the budget constraint captured here — when a design choice seems odd
(no ALB, backend on a single public EC2 instance), this is the reason.

## The trade we're making

**Accepted:** one extra small EC2 instance (~$15/month) and the operational
fiddliness of forcing all of the app instance's egress through a forward
proxy, in exchange for real network isolation: the backend runs on a
private instance with no public IP and no internet route.

**Not accepted:** the managed-service bill that usually comes with private
subnets. No NAT Gateway, no ALB, and **no paid interface endpoints** — the
app instance reaches AWS APIs through the same allow-listed forward proxy
as Auth0, plus the *free* S3 gateway endpoint for ECR image layers. (The
endpoint-heavy version of this design needs ~9 interface endpoints at
~$7.5+/month each — more than the NAT + ALB it avoids. See "What we
deliberately avoid".)

The standing mitigations either way:

- Only the proxy instance is internet-facing; Caddy binds 443 (and 80 for
  redirect), nothing else. The backend has no public IP at all.
- Outbound from the app instance is allow-listed by domain at the proxy
  (Auth0, AWS service endpoints, Sentry/PostHog if used) — everything
  else fails.
- RDS is private, reachable only from the app instance's security group.
- No SSH from the internet; management via SSM (proxy box) and an EC2
  Instance Connect Endpoint — free — for the private box (Session
  Manager does not work through an HTTPS proxy).
- No long-lived AWS keys anywhere: GitHub deploys via OIDC roles,
  instances use their IAM roles.
- TLS everywhere: CloudFront + ACM for the frontends, Caddy DNS-01 certs
  for the API.

The network-lockdown details live in
[caddy-ec2-implementation-notes.md](implementation-sketch/caddy-ec2-implementation-notes.md#network-lockdown).

## Target shape (cheapest hardened)

```text
Route 53
  ├── CloudFront + S3            (frontends)
  └── api.<domain> → Elastic IP
        └── PUBLIC proxy EC2 (public subnet)
              ├── Caddy        (inbound TLS + reverse proxy)
              └── Squid        (outbound forward proxy, domain allow-list)
                    ↓ private VPC route
        PRIVATE app EC2 (private subnet, no public IP, no internet route)
              └── backend container (Docker Compose)
                    ├── egress → proxy EC2 only (Auth0, AWS APIs)
                    ├── ECR layers → free S3 gateway endpoint
                    └── private RDS PostgreSQL
```

No ALB. No NAT Gateway. No paid interface endpoints. No RDS Proxy.

## Monthly budget (per full environment)

Rough On-Demand figures, USD. Sydney (`ap-southeast-2`) prices run slightly
above us-east-1, so treat these as the floor of the range.

| Service | Purpose | Rough monthly cost |
|---|---|---:|
| Route 53 hosted zone | DNS | ~$0.50 |
| S3 frontend buckets | Static frontend files | <$1 |
| CloudFront | CDN for frontends | ~$0–$3 at low traffic |
| EC2 `t4g.small` (proxy) | Caddy inbound + Squid outbound | ~$12–$16 |
| EC2 `t4g.small` (app) | Backend containers, private subnet | ~$12–$16 |
| Public IPv4 | Elastic IP for the proxy EC2 (app EC2 has none) | ~$3.65 |
| EBS gp3 2 × 20–30 GB | Instance disks | ~$4–$6 |
| RDS PostgreSQL `db.t4g.micro` | Managed Postgres (core + response DBs on one instance) | ~$12 |
| RDS storage 20 GB | Database disk | ~$2–$4 |
| Secrets Manager / SSM | Secrets and config | ~$0–$2 |
| KMS key | Customer-managed encryption key | ~$1 |
| CloudWatch logs | Basic logs | ~$1–$5 |

**Expected total: ~$50–$70 USD/month (~$75–$105 AUD).**
With `db.t4g.small` instead of `db.t4g.micro`: ~$65–$85 USD (~$98–$128 AUD).
(The earlier single-public-EC2 draft was ~$35–$50; the isolation upgrade
costs roughly one extra `t4g.small`.)

dev costs almost nothing on top of this: it deploys the Security stack only
(KMS + secrets), with app, databases, and frontends running locally — see
[environments.md](environments.md).

## What we deliberately avoid, and why

| Avoided service | Monthly saving (rough) | Why it's safe to skip now |
|---|---:|---|
| ALB | ~$20+ | Caddy on the proxy instance terminates HTTPS and reverse proxies to the private app instance |
| NAT Gateway | ~$50+ hourly + data | The app instance's only egress is the allow-listed forward proxy — a NAT would grant broad outbound access we specifically don't want |
| Paid interface endpoints | ~$7.5+ EACH (the "clean" version needs ~9 → ~$70) | AWS API calls (Secrets Manager, KMS, SES, ECR auth) ride the forward proxy like all other egress; only the FREE S3 gateway endpoint is provisioned (ECR layers live in S3) |
| SSM interface endpoint trio | ~$22 | Session Manager can't traverse an HTTPS proxy; the private box is reached via a free EC2 Instance Connect Endpoint instead |
| RDS Proxy | ~$11+ | Connection pressure isn't real with one Gunicorn service; PgBouncer is the cheaper fallback if it becomes real |
| Amplify Hosting | build minutes + hosting | Replaced by S3 + CloudFront, which is cheaper and CDK-controlled |

## Upgrade triggers

The cheap shape is a starting point, not a ceiling. Revisit when:

- **Proxy fiddliness costs more than money** — if debugging
  proxied AWS API traffic (boto3/SSM-agent/ECR through Squid) becomes a
  recurring tax, buy back the time with interface endpoints for the
  painful services only (~$7.5/month each), starting with the SSM trio.
- **Traffic outgrows one app instance** → the Compose file ports cleanly
  to ECS + ALB (the escape hatch anticipated in
  [Phase 6 of the plan](implementation-sketch/core-sketch-plan.md#phase-6--hardening-post-cutover-prioritized-backlog)).
- **DB connections become a bottleneck** → add PgBouncer to the Compose
  stack first; RDS Proxy only after that.
- **Availability matters more than cost** → RDS multi-AZ, then a second
  app instance behind an ALB (the proxy instance is a single point of
  failure by design at this price point).
