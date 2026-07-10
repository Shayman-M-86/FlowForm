# Docker Compose Design and Hardening (proxy + app instances)

Companion to [caddy-ec2-implementation-notes.md](caddy-ec2-implementation-notes.md)
(network shape, security groups, route tables) and
[host-hardening.md](host-hardening.md) (the Linux machines themselves).
This doc covers what runs **inside Docker** on the two EC2 instances and
how the containers are configured and constrained.
For the operational checks that must still be proven in CDK, host bootstrap,
IAM, and staging, see
[ec2-compose-due-diligence-checklist.md](ec2-compose-due-diligence-checklist.md).

Framing: Compose networking and file-secrets are conveniences here, not
the security boundary. The real isolation comes from AWS route tables,
security groups, the Squid allow-list, and the host firewalls — Docker
hardening is the containment layer inside that.

## Assumed values

| Thing | Value |
|---|---|
| Proxy EC2 private IP | `10.0.1.10` (example) |
| App EC2 private IP | `10.0.11.10` (example) |
| Public API DNS | `api.<public_site_domain>` |
| Forward-proxy port | `3128` |
| Backend port (container AND host) | `5000` (Gunicorn's port in `backend.Dockerfile`) |
| Health check | `python /app/scripts/healthcheck.py` in-container; `/api/v1/system/health/ready` over HTTP |

## Proxy instance layout

```text
/opt/flowform-proxy/
  docker-compose.yml        # caddy + squid
  .env                      # PROXY_PRIVATE_IP, APP_PRIVATE_IP, API_DOMAIN, image refs
  caddy/Caddyfile
  squid/squid.conf
  squid/allowed-domains.txt
```

Compose sketch (`caddy` is the custom ECR image built with xcaddy +
`caddy-dns/route53` — stock `caddy:2-alpine` cannot do the decided
Route 53 DNS-01 flow):

```yaml
name: flowform-proxy

services:
  caddy:
    image: ${CADDY_IMAGE:?ECR ref of the xcaddy+route53 build}
    restart: unless-stopped
    ports:
      - "80:80/tcp"
      - "443:443/tcp"
    environment:
      API_DOMAIN: ${API_DOMAIN:?}
      APP_PRIVATE_IP: ${APP_PRIVATE_IP:?}
      AWS_REGION: ${AWS_REGION}   # route53 provider via instance role/IMDS
    volumes:
      - ./caddy/Caddyfile.proxy:/etc/caddy/Caddyfile:ro
      - caddy_data:/data          # cert storage must survive restarts
      - caddy_config:/config
    read_only: true
    tmpfs: [/tmp]
    cap_drop: [ALL]
    cap_add: [NET_BIND_SERVICE]
    security_opt: ["no-new-privileges:true"]
    logging: {driver: json-file, options: {max-size: "10m", max-file: "5"}}
    networks: [proxy_net]

  squid:
    image: ubuntu/squid:latest
    restart: unless-stopped
    environment:
      SQUID_APP_SOURCE_CIDR: ${SQUID_APP_SOURCE_CIDR:?exact app EC2 source CIDR, usually APP_PRIVATE_IP/32}
    # Bound to the PRIVATE interface, never 0.0.0.0 — plus the security
    # group only admits 3128 from the app SG. Two layers, same rule.
    ports:
      - "${PROXY_PRIVATE_IP:?}:3128:3128/tcp"
    volumes:
      - ./squid/squid.conf:/etc/squid/squid.conf.template:ro
      - ./squid/allowed-domains.txt:/etc/squid/allowed-domains.txt:ro
      - squid_logs:/var/log/squid
    read_only: true
    tmpfs: [/run, /tmp, /var/spool/squid]
    cap_drop: [ALL]
    # ubuntu/squid starts as root then drops to proxy; these are only for
    # that privilege drop, not for binding low ports.
    cap_add: [SETGID, SETUID]
    security_opt: ["no-new-privileges:true"]
    entrypoint: ["/bin/sh", "-ec"]
    command: >
      sed "s|__APP_SOURCE_CIDR__|$${SQUID_APP_SOURCE_CIDR}|g"
      /etc/squid/squid.conf.template > /tmp/squid.conf
      && exec squid -N -f /tmp/squid.conf
    logging: {driver: json-file, options: {max-size: "10m", max-file: "5"}}
    networks: [proxy_net]

networks:
  proxy_net: {driver: bridge}

volumes:
  caddy_data:
  caddy_config:
  squid_logs:
```

### Caddyfile

TLS terminates here; the hop to the app instance is plain HTTP over the
private VPC — acceptable because it never crosses the public internet.

```caddyfile
{
 log {
  output stdout
  format json
 }
}

{$API_DOMAIN} {
 encode zstd gzip

 tls {
  dns route53
 }

 header {
  Strict-Transport-Security "max-age=31536000; includeSubDomains"
  X-Content-Type-Options "nosniff"
  Referrer-Policy "strict-origin-when-cross-origin"
  -Server
 }

 reverse_proxy http://{$APP_PRIVATE_IP}:5000 {
  health_uri /api/v1/system/health/ready
  health_interval 30s
  health_timeout 5s
 }
}
```

Proxy only to the app instance's backend port — never to broad internal
ranges.

### Squid: the egress policy engine

Explicit proxy mode, CONNECT-based domain allow-listing, **no TLS
interception** (no SSL-Bump — invasive, detectable, unnecessary here).

```squidconf
http_port 3128

acl app_ec2 src __APP_SOURCE_CIDR__
acl SSL_ports port 443
acl CONNECT method CONNECT
acl allowed_domains dstdomain "/etc/squid/allowed-domains.txt"

http_access deny !app_ec2
http_access deny CONNECT !SSL_ports
http_access allow app_ec2 CONNECT allowed_domains
http_access deny all

cache deny all

via off
forwarded_for delete
request_header_access X-Forwarded-For deny all
request_header_access Via deny all

access_log stdio:/var/log/squid/access.log
```

`allowed-domains.txt` — start strict, exact hosts, one AWS service at a
time. Never `.amazonaws.com` or `.auth0.com` wholesale:

```text
auth.flow-form.com.au
<tenant>.au.auth0.com
secretsmanager.ap-southeast-2.amazonaws.com
kms.ap-southeast-2.amazonaws.com
ssm.ap-southeast-2.amazonaws.com
email.ap-southeast-2.amazonaws.com
api.ecr.ap-southeast-2.amazonaws.com
<aws-account-id>.dkr.ecr.ap-southeast-2.amazonaws.com
```

Notes:

- `email.*` is the **SESv2 API** — the backend sends via boto3, not SMTP.
- No `sts.*`: the app uses its instance role directly, nothing assumes
  roles at runtime.
- No broad wildcards: replace the Auth0 tenant and ECR account placeholders
  with exact hosts during bootstrap.
- `logs.*` only if/when the CloudWatch agent or awslogs driver ships from
  this box.
- Add Sentry/PostHog ingest hosts only if those integrations are enabled.
- **Watch the deny log** — it is simultaneously the "which AWS host did I
  forget" debugger and the exfiltration alarm.

## App instance layout

```text
/opt/flowform-app/
  docker-compose.yml          # backend only (repo source: docker-compose.app.yml)
/opt/flowform/backend.env     # non-secret FLOWFORM_* config, written by bootstrap from SSM
/run/flowform/secrets/        # tmpfs; written by bootstrap from Secrets Manager
  DATABASE_CORE_APP_PASSWORD.secret.txt
  DATABASE_RESPONSE_APP_PASSWORD.secret.txt
  FLOWFORM_APP_SECRET_KEY.secret.txt
  FLOWFORM_AUTH0_MGMT_SECRET.secret.txt
```

Secret names, `*_FILE` env vars, and the tmpfs bootstrap all follow the
existing convention (see the Secrets and Configuration Bootstrap section
of the notes doc) — do not invent new names.

Backend service sketch (`infra/docker/docker-compose.app.yml`):

```yaml
services:
  backend:
    image: ${BACKEND_IMAGE:?}          # pin to @sha256: digest in prod
    restart: unless-stopped
    init: true
    command: ["/opt/flowform/backend-venv/bin/gunicorn", "-c", "gunicorn.conf.py", "--worker-tmp-dir", "/tmp", "--no-control-socket", "wsgi:app"]
    # Bind to the private interface only — never 0.0.0.0. The SG only
    # admits 5000 from the proxy SG anyway; layers must agree.
    ports:
      - "${APP_PRIVATE_IP:?}:5000:5000/tcp"
    env_file:
      - /opt/flowform/backend.env
    environment:
      HTTP_PROXY: "http://${PROXY_PRIVATE_IP}:3128"
      HTTPS_PROXY: "http://${PROXY_PRIVATE_IP}:3128"
      UV_CACHE_DIR: /tmp/uv-cache
      # CAUTION: Python (requests/boto3) does NOT understand CIDR entries
      # in NO_PROXY — 10.0.0.0/16 is honored by the Go-based Docker
      # daemon but silently ignored by the app. Use hostname/suffix
      # entries for everything the backend itself dials.
      NO_PROXY: "localhost,127.0.0.1,169.254.169.254,.rds.amazonaws.com"
      # *_FILE secret envs + FLOWFORM_ENV as in docker-compose.app.yml
    secrets:
      - DATABASE_CORE_APP_PASSWORD
      - DATABASE_RESPONSE_APP_PASSWORD
      - FLOWFORM_APP_SECRET_KEY
      - FLOWFORM_AUTH0_MGMT_SECRET
    read_only: true
    tmpfs: [/tmp, /app/logs]
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    pids_limit: 256
    healthcheck:
      test: ["CMD", "python", "/app/scripts/healthcheck.py"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
    logging: {driver: json-file, options: {max-size: "10m", max-file: "5"}}
```

`read_only: true` prerequisite: prod app logging must go to **stdout as
JSON** (`FLOWFORM_LOGGING_LOG_JSON=true`, no
`FLOWFORM_LOGGING_LOG_FILE` / legacy `LOG_FILE`) instead of the dev
`logs/app.log` file — stdout logging is the better production shape
regardless (Docker owns rotation, CloudWatch can ship it). `/app/logs`
is tmpfs only to satisfy the current bootstrap logger before settings are
loaded; nothing should rely on it for durable logs.

### Docker daemon proxy (`/etc/docker/daemon.json` on the app instance)

The daemon needs the proxy too, or ECR pulls fail. The daemon is Go, so
CIDR in `no-proxy` works here; the S3 entry keeps image layers on the
free gateway endpoint instead of hairpinning through Squid:

```json
{
  "proxies": {
    "http-proxy": "http://10.0.1.10:3128",
    "https-proxy": "http://10.0.1.10:3128",
    "no-proxy": "localhost,127.0.0.1,169.254.169.254,10.0.0.0/16,.s3.ap-southeast-2.amazonaws.com"
  },
  "log-driver": "json-file",
  "log-opts": {"max-size": "10m", "max-file": "5"}
}
```

Host-side bootstrap on the app instance must use the same proxy path for
AWS API calls before Compose starts. Export `HTTP_PROXY`/`HTTPS_PROXY`
for the bootstrap process and keep `NO_PROXY` aligned with the daemon:
IMDS, localhost, the VPC CIDR/RDS path, and the S3 gateway endpoint must
stay direct. Bootstrap should fetch SSM parameters, Secrets Manager
values, and any KMS decrypts through Squid; the app host should not get a
temporary public route or direct internet egress just to bootstrap.

The proxy instance is different: it is in the public subnet and may pull
the Caddy image directly over outbound HTTPS using its instance role. Its
host firewall/security group egress still needs to allow the specific
paths required for ECR auth and image layers, plus ACME and Route 53 for
Caddy.

## Rules

1. **Fail closed.** If Squid is down, the app instance has no internet —
   by design. Never "fix" an outage with a NAT route, a public IP, or a
   `0.0.0.0/0` outbound rule.
2. **All the layers must agree.** Container port binding (private IP),
   security group, host firewall, and route table each independently
   enforce the same policy — a mistake in one is caught by the others.
3. **No Docker socket in app containers.** Mounting
   `/var/run/docker.sock` is host-level access.
4. **Secrets as files, never env values.** The `*_FILE` pattern is
   already app-wide; env vars leak through inspection, crash reports,
   and `docker inspect`.
5. **No builds on production.** No git, pip, npm, compilers on either
   instance. Images build in CI, push to ECR, instances only pull —
   pinned to immutable digests in prod.
6. **No PgBouncer/Redis/workers until an actual need exists** (they are
   upgrade triggers in [cost-model.md](../cost-model.md), not baseline
   components).
7. **The proxy box is the residual trust boundary.** If it is fully
   compromised the attacker owns both gateways — which is why it runs
   nothing but Caddy and Squid, and why
   [host-hardening.md](host-hardening.md) applies most strictly there.

## Verification commands

From the app instance:

```bash
# Docker daemon can authenticate to ECR through the proxy and pull layers
# through the S3 gateway endpoint.
docker pull <backend-image-ref>
# Bootstrap can read config/secrets through the proxy.
aws ssm get-parameter --name /flowform/<env>/backend/example --with-decryption
aws secretsmanager get-secret-value --secret-id flowform/<scope>/app-secrets
# allowed through Squid
curl --proxy http://10.0.1.10:3128 https://<tenant>.au.auth0.com/.well-known/jwks.json
# blocked by Squid (must fail)
curl --proxy http://10.0.1.10:3128 https://example.com
# no direct internet (must hang/fail — no route)
curl --max-time 5 https://example.com
# RDS direct over VPC
nc -vz <rds-endpoint> 5432
```

From anywhere:

```bash
curl https://api.<domain>/api/v1/system/health/ready   # via Caddy
curl http://<app-private-ip>:5000/                     # must be unreachable
```
