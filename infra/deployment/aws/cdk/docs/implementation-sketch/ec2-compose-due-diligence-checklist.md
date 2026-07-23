# EC2 Compose Due Diligence Checklist

This is a caution checklist for the split EC2 Compose design:

- public proxy EC2: Caddy + Squid
- private app EC2: backend only
- no NAT Gateway, no ALB, no public app IP
- app egress only through Squid, except direct private/VPC paths such as RDS,
  IMDS, DNS, NTP, and the S3 gateway endpoint for ECR layers

Treat this as a review and staging-proof checklist, not as a claim that the
current Compose files are wrong. The Compose split is mostly done; the remaining
risk lives in CDK networking, host bootstrap, IAM, endpoint policy, and smoke
testing.

## How to use this checklist

Before considering the EC2 runtime production-ready:

1. Verify each item against the actual CDK, user data/bootstrap scripts, IAM
   policies, security groups, route tables, and staging hosts.
2. Prefer evidence from a staging command or AWS resource inspection over
   intent in a doc.
3. If a check fails, fix the enforcing layer first. Do not weaken the Compose
   hardening or add a broad network route as a shortcut.

## App Instance Egress

- [ ] The app EC2 has no public IP.
- [ ] The app private subnet route table has no `0.0.0.0/0` route to an IGW or
  NAT Gateway.
- [ ] App security group egress allows the proxy EC2 on `3128`.
- [ ] App security group egress allows RDS on `5432`.
- [ ] App security group egress allows the S3 gateway endpoint path needed for
  ECR layer downloads.
- [ ] App security group egress does not allow arbitrary internet `443`.
- [ ] Host firewall mirrors the same policy: proxy `3128`, RDS `5432`, S3
  endpoint `443`, VPC DNS, Amazon Time Sync, and nothing broad.
- [ ] From the app host, direct `curl --max-time 5 https://example.com` fails.
- [ ] From the app host, `curl --proxy http://<proxy-private-ip>:3128
  https://example.com` fails with a Squid denial.
- [ ] From the app host, `curl --proxy http://<proxy-private-ip>:3128
  https://<auth0-tenant>/.well-known/jwks.json` succeeds.

## Docker Pulls And ECR

ECR pulls are not just app-container traffic. Docker pulls happen on the EC2
host before the backend container exists.

- [ ] App host Docker daemon has `HTTP_PROXY` and `HTTPS_PROXY` configured for
  the proxy EC2.
- [ ] App host Docker daemon `no-proxy` includes localhost, IMDS, VPC/RDS paths,
  and the S3 gateway endpoint pattern.
- [ ] ECR API/auth/manifest calls can reach the required regional ECR endpoints
  through Squid.
- [ ] ECR image layer downloads use the S3 gateway endpoint, not direct
  internet.
- [ ] The S3 gateway endpoint is associated only with the route tables that
  need it.
- [ ] The S3 endpoint policy is intentionally scoped. Do not leave a broad
  default policy by accident.
- [ ] `docker pull <backend-image-ref>` works from the locked-down app host.
- [ ] `docker pull <caddy-image-ref>` works from the proxy host.
- [ ] Production image refs are pinned by digest, not mutable tags.

## Host Bootstrap

Docker daemon proxy config does not configure every host process. Bootstrap,
package updates, agents, and ad hoc commands need their own explicit path.

- [ ] App host bootstrap exports `HTTP_PROXY` and `HTTPS_PROXY` before AWS API
  calls.
- [ ] App host bootstrap `NO_PROXY` includes `localhost`, `127.0.0.1`,
  `169.254.169.254`, RDS/private hostnames or suffixes, and any direct endpoint
  paths.
- [ ] Bootstrap fetches SSM parameters through the intended path.
- [ ] Bootstrap fetches Secrets Manager values through the intended path.
- [ ] Bootstrap KMS decrypt operations work through the intended path.
- [ ] Bootstrap does not temporarily attach a public IP, add a NAT route, or
  open direct internet egress.
- [ ] `/opt/flowform/backend.env` is generated, root-owned, not world-readable,
  and validated before Compose restart.
- [ ] `/opt/flowform/proxy.env` is generated, root-owned, not world-readable,
  and validated before Compose restart.
- [ ] `/run/flowform/secrets` is tmpfs, root-owned, and mode `0700`.
- [ ] Secret files under `/run/flowform/secrets` are mode `0600`.
- [ ] Secret files are recreated on reboot/deploy and are not backed up to EBS
  snapshots or copied into project folders.

## NO_PROXY And IMDS

`NO_PROXY` is security and availability plumbing, not convenience.

- [ ] Backend container `NO_PROXY` includes `169.254.169.254` so instance-role
  credential lookups do not go through Squid.
- [ ] Backend container `NO_PROXY` uses hostnames or suffixes only. Do not rely
  on CIDR entries for Python requests/boto3.
- [ ] Docker daemon `no-proxy` may use CIDR entries because the daemon is Go
  based.
- [ ] App bootstrap `NO_PROXY` is tested independently from Docker daemon
  `no-proxy`.
- [ ] Caddy container can reach IMDS with IMDSv2 and hop limit >= 2.
- [ ] Backend container can reach IMDS with IMDSv2 and hop limit >= 2.

## Squid Allow-List

The allow-list should start strict and grow only from observed need.

- [ ] Auth0 tenant host is exact.
- [ ] Auth0 custom domain, if used, is exact and included.
- [ ] AWS regional hosts are exact.
- [ ] ECR registry host is account-specific, not `.amazonaws.com` wholesale.
- [ ] No `sts.*` is added unless a real runtime or bootstrap flow needs it.
- [ ] No broad `.auth0.com` or `.amazonaws.com` wildcard is added.
- [ ] Sentry, PostHog, webhooks, or other future integrations are added only as
  exact required hosts.
- [ ] Squid deny logs are easy to inspect during deploy and incident response.
- [ ] Repeated deny logs have an alert or at least a day-one operational runbook.

## Proxy EC2 Boundary

The proxy EC2 is now both the public entry point and the controlled outbound
gateway. Harden it as the highest-value host in this design.

- [ ] Proxy public inbound allows only `80` and `443`.
- [ ] Proxy private inbound allows `3128` only from the app security group.
- [ ] Proxy outbound allows Caddy ACME and Route 53 needs.
- [ ] Proxy outbound allows proxy-side ECR image pulls.
- [ ] Proxy outbound allows only the destinations Squid is expected to dial.
- [ ] Proxy role has hosted-zone-scoped Route 53 permissions, not broad DNS
  power.
- [ ] Proxy role can pull only the images it needs.
- [ ] Proxy host has no app secrets.
- [ ] Proxy host runs only Caddy, Squid, the management agent, and baseline
  host services.
- [ ] Caddy `/data` volume survives container replacement so cert state is not
  lost repeatedly.
- [ ] Caddy certificate issuance and renewal are tested in staging.

## App Backend Exposure

- [ ] `compose.app.yml` binds backend only to
  `${APP_PRIVATE_IP}:5000:5000/tcp`.
- [ ] App security group allows backend `5000` only from the proxy security
  group.
- [ ] Host firewall allows backend `5000` only from the proxy private IP or
  proxy security group equivalent.
- [ ] `curl http://<app-private-ip>:5000/...` fails from outside the proxy path.
- [ ] `curl https://api.<domain>/api/v1/system/health/ready` succeeds through
  Caddy.
- [ ] Private HTTP from Caddy to backend is accepted as an explicit trade-off.
  If compliance requirements change, revisit TLS or mTLS between proxy and app.

## IAM And Endpoint Policies

- [ ] Proxy instance role is separate from app instance role.
- [ ] Proxy role has Route 53 permissions scoped to the hosted zone used for
  DNS-01.
- [ ] Proxy role has ECR pull permissions only as needed.
- [ ] App role can read only the SSM parameters and Secrets Manager secrets for
  the relevant scope.
- [ ] App role can use only the relevant KMS key.
- [ ] App role has SES permissions only as needed.
- [ ] App role has ECR pull permissions only as needed.
- [ ] Any VPC endpoint policy is intentionally scoped. The default broad policy
  should not be accepted silently.
- [ ] If CloudWatch log shipping is enabled, the required endpoint/proxy path
  and IAM permissions are designed explicitly.

## Runtime File And Logging Assumptions

- [ ] Backend production logging goes to stdout JSON:
  `FLOWFORM_LOGGING_LOG_JSON=true`.
- [ ] `FLOWFORM_LOGGING_LOG_FILE` is unset in production.
- [ ] No legacy `LOG_FILE` value is set in production env files.
- [ ] Backend writes only to `/tmp`, `/app/logs` tmpfs, stdout, databases, or
  explicitly designed external storage.
- [ ] Gunicorn starts with `--worker-tmp-dir /tmp`.
- [ ] Gunicorn control socket is disabled with `--no-control-socket`.
- [ ] Docker `json-file` log rotation is configured on proxy and app services.
- [ ] If logs are shipped to CloudWatch, the shipping path is tested after
  lockdown.

## Env Files

`/opt/flowform/backend.env` does two jobs: Compose interpolation and backend
runtime config. `/opt/flowform/proxy.env` does proxy Compose interpolation.

- [ ] Env files are generated by bootstrap rather than hand-edited on the host.
- [ ] Env files contain no secret values.
- [ ] Env files are root-owned and not world-readable.
- [ ] Env files are validated before `docker compose up -d`.
- [ ] `BACKEND_IMAGE` and `CADDY_IMAGE` are immutable digest refs.
- [ ] `APP_PRIVATE_IP` and `PROXY_PRIVATE_IP` match the actual ENI private IPs.
- [ ] `SQUID_APP_SOURCE_CIDR` is exact, usually `<APP_PRIVATE_IP>/32`.
- [ ] `API_DOMAIN` matches the Route 53 record and Caddy site block.
- [ ] `AWS_REGION` matches deployed resources.
- [ ] DB host/name/user settings match RDS.
- [ ] Auth0, KMS, linkage-secret, SES, and logging settings match the target
  environment.

## Staging Smoke Test

Do not treat local Compose proof as AWS proof. Before prod:

- [ ] Proxy instance starts Caddy and Squid from pulled images.
- [ ] App instance pulls backend image after lockdown.
- [ ] App bootstrap fetches SSM, Secrets Manager, and KMS values after lockdown.
- [ ] App host direct internet curl fails.
- [ ] App host proxy curl to an allowed host succeeds.
- [ ] App host proxy curl to a blocked host fails and is visible in Squid logs.
- [ ] Backend container can use instance-role credentials.
- [ ] Backend container can reach Auth0 through Squid.
- [ ] Backend container can reach KMS, Secrets Manager, and SES through Squid.
- [ ] Backend connects to both RDS databases over the VPC.
- [ ] RDS rejects connections from anything except the app security group.
- [ ] Caddy obtains a certificate through Route 53 DNS-01.
- [ ] Caddy can renew or at least perform a staging renewal dry run.
- [ ] Public API health succeeds through Caddy.
- [ ] Backend private port is unreachable except from the proxy path.
- [ ] Secrets exist only in tmpfs/root-owned files on the app host.
- [ ] Restarting containers does not lose Caddy cert state or backend config.

## Escalation Triggers

Revisit the design if any of these become true:

- Squid allow-list churn becomes frequent or operationally painful.
- AWS API proxying is brittle for recurring services.
- Compliance requires encryption on the proxy-to-app hop.
- CloudWatch or security tooling requires many additional endpoints.
- The app needs third-party integrations with broad or unstable domains.
- The proxy EC2 becomes too much residual trust for the threat model.

Likely upgrades in those cases: targeted VPC interface endpoints, mTLS between
proxy and app, ALB/private target architecture, or a managed egress strategy.
