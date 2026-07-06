# Cost Model

This doc records **why the deployment architecture looks the way it does**:
it is the cheapest setup that still resembles a proper production deployment.
The stack shape in [aws-overview.md](aws-overview.md) and the
[deployment plan](implementation-sketch/core-sketch-plan.md) are downstream
of the budget constraint captured here — when a design choice seems odd
(no ALB, backend on a single public EC2 instance), this is the reason.

## The trade we're making

**Accepted:** less isolation than a textbook AWS setup. The backend runs on
one public EC2 instance rather than in a private subnet behind a load
balancer, and there is no NAT Gateway, second instance, or RDS Proxy.

**Not accepted:** actual exposure. The mitigations that keep the cheap shape
defensible:

- Only Caddy binds public ports (443, optionally 80 for redirect); the
  Flask/Gunicorn container has no host-published port.
- RDS is private, reachable only from the EC2 security group on 5432.
- No SSH — instance access is SSM Session Manager only.
- No long-lived AWS keys anywhere: GitHub deploys via OIDC roles, Caddy
  gets Route 53 access via the instance role.
- TLS everywhere: CloudFront + ACM for the frontends, Caddy DNS-01 certs
  for the API.

The network-lockdown details live in
[caddy-ec2-implementation-notes.md](implementation-sketch/caddy-ec2-implementation-notes.md#network-lockdown).

## Target shape (cheapest sensible)

```text
Route 53
  ├── CloudFront + S3          (frontends)
  └── api.<domain> → public EC2 instance
        ├── Caddy container
        └── backend container
              ↓
        private RDS PostgreSQL
```

No ALB. No NAT Gateway. No second EC2. No RDS Proxy. No private backend
subnet yet.

## Monthly budget (per full environment)

Rough On-Demand figures, USD. Sydney (`ap-southeast-2`) prices run slightly
above us-east-1, so treat these as the floor of the range.

| Service | Purpose | Rough monthly cost |
|---|---|---:|
| Route 53 hosted zone | DNS | ~$0.50 |
| S3 frontend buckets | Static frontend files | <$1 |
| CloudFront | CDN for frontends | ~$0–$3 at low traffic |
| EC2 `t4g.small` | Caddy + backend | ~$12–$16 |
| Public IPv4 | Elastic IP for EC2 | ~$3.65 |
| EBS gp3 30 GB | EC2 disk | ~$2.50–$3 |
| RDS PostgreSQL `db.t4g.micro` | Managed Postgres (core + response DBs on one instance) | ~$12 |
| RDS storage 20 GB | Database disk | ~$2–$4 |
| Secrets Manager / SSM | Secrets and config | ~$0–$2 |
| KMS key | Customer-managed encryption key | ~$1 |
| CloudWatch logs | Basic logs | ~$1–$5 |

**Expected total: ~$35–$50 USD/month (~$52–$75 AUD).**
With `db.t4g.small` instead of `db.t4g.micro`: ~$50–$65 USD (~$75–$98 AUD).

dev costs almost nothing on top of this: it deploys the Security stack only
(KMS + secrets), with app, databases, and frontends running locally — see
[environments.md](environments.md).

## What we deliberately avoid, and why

| Avoided service | Monthly saving (rough) | Why it's safe to skip now |
|---|---:|---|
| ALB | ~$20+ | Caddy terminates HTTPS and reverse proxies for the cost of the EC2 it already runs on |
| NAT Gateway | ~$35+ hourly + data | The EC2 instance is public and uses the Internet Gateway for outbound |
| Second EC2 | ~$12–16 | No isolation/HA need until traffic or risk justifies it |
| RDS Proxy | ~$11+ | Connection pressure isn't real with one Gunicorn service; PgBouncer is the cheaper fallback if it becomes real |
| VPC interface endpoints | ~$7+ each | Useful hardening later, not cheapest at the start |
| Amplify Hosting | build minutes + hosting | Replaced by S3 + CloudFront, which is cheaper and CDK-controlled |

## Upgrade triggers

The cheap shape is a starting point, not a ceiling. Revisit when:

- **Traffic outgrows one instance** → the Compose file ports cleanly to
  ECS + ALB (the escape hatch anticipated in
  [Phase 6 of the plan](implementation-sketch/core-sketch-plan.md#phase-6--hardening-post-cutover-prioritized-backlog)).
- **DB connections become a bottleneck** → add PgBouncer to the Compose
  stack first; RDS Proxy only after that.
- **Availability matters more than cost** → RDS multi-AZ, then a second
  app instance behind an ALB.
- **Isolation requirements tighten** → move EC2 to a private subnet
  (which is what forces the ALB + NAT/endpoint spend — take it as a
  package, not piecemeal).
