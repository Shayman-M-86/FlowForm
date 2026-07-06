# Custom Caddy image for FlowForm.
#
# Stock Caddy cannot solve ACME DNS-01 challenges via Route 53, which is how
# the EC2 host obtains/renews the api.<domain> certificate (no inbound HTTP
# needed for validation). We build Caddy with xcaddy and add the
# caddy-dns/route53 module, then copy the resulting binary onto the matching
# stock Caddy runtime image so we keep its default Caddyfile handling,
# entrypoint, and volumes.
#
# Pin CADDY_VERSION so the builder and runtime stages stay in lockstep.
ARG CADDY_VERSION=2.10.2

FROM caddy:${CADDY_VERSION}-builder AS builder

# The builder image pins GOTOOLCHAIN=local, so Go won't auto-upgrade when a
# plugin requires a newer toolchain than the image ships (e.g. caddy-dns/route53
# needs Go >= 1.25). Allow the auto-download so the build tracks plugin
# requirements without chasing builder-image versions.
ENV GOTOOLCHAIN=auto

RUN xcaddy build \
    --with github.com/caddy-dns/route53

FROM caddy:${CADDY_VERSION}

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
