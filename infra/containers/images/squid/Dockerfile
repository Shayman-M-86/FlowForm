# syntax=docker/dockerfile:1

FROM ubuntu/squid:6.6-24.04_edge@sha256:8a3baed477e2c282ab8aa5edad442f69873246964f225c5c2ae8364b6610963c

COPY squid.conf.template /etc/squid/squid.conf.template
COPY allowed-domains.txt /etc/squid/allowed-domains.txt
COPY --chmod=0755 entrypoint.sh /usr/local/bin/flowform-squid-entrypoint
COPY --chmod=0755 healthcheck.sh /usr/local/bin/flowform-squid-healthcheck

# Validate the checked-in template during the image build with inert source
# addresses. Runtime source CIDRs are rendered and validated again at startup.
RUN sed \
      -e 's|__APP_SOURCE_CIDR__|127.0.0.1/32|g' \
      -e 's|__DB_BOOTSTRAP_SOURCE_CIDR__|127.0.0.1/32|g' \
      /etc/squid/squid.conf.template > /tmp/flowform-squid.conf \
    && squid -k parse -f /tmp/flowform-squid.conf \
    && rm -f /tmp/flowform-squid.conf

ENTRYPOINT ["/usr/local/bin/flowform-squid-entrypoint"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["/usr/local/bin/flowform-squid-healthcheck"]
