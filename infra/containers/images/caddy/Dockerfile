# syntax=docker/dockerfile:1

# AWS staging uses Route 53 DNS-01 certificate issuance, and the public API uses
# Caddy's third-party rate-limit handler. Neither module is bundled with the
# stock Caddy image, so build one pinned binary with xcaddy.
# Both stages use immutable official-image index digests; the release workflow
# must build linux/amd64 to match the current x86_64 EC2/AMI contract.
FROM caddy:2.11.4-builder-alpine@sha256:8e89605351333ad2cc2f3bcc95275a2ccc427f88914050e86a5fde0fd77a63c4 AS builder

RUN xcaddy build v2.11.4 \
    --with github.com/caddy-dns/route53@v1.6.2 \
    --with github.com/mholt/caddy-ratelimit@5625512f24f6f59d6f64fb3aafe5eecff0b286db \
    --output /usr/bin/caddy

FROM caddy:2.11.4-alpine@sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
COPY Caddyfile /etc/caddy/Caddyfile
COPY rate-limits.caddy /etc/caddy/rate-limits.caddy

# Fail the image build if the copied binary does not contain the exact modules
# required by the container-owned Caddy configuration.
RUN caddy list-modules | grep -Fxq 'dns.providers.route53'
RUN caddy list-modules | grep -Fxq 'http.handlers.rate_limit'

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:2019/config/ || exit 1
