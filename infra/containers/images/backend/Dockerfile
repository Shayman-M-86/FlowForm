# syntax=docker/dockerfile:1

FROM python:3.14.6-slim-trixie@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6

COPY --from=ghcr.io/astral-sh/uv:0.11.31@sha256:ecd4de2f060c64bea0ff8ecb182ddf46ba3fcccdc8a60cfdbaf20d1a047d7437 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/flowform/backend-venv \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    WEB_CONCURRENCY=2 \
    TIMEOUT=60


WORKDIR /app

# RDS IAM authentication requires TLS. Pin the regional AWS trust bundle so
# verify-full validates both the certificate chain and the RDS endpoint name.
ADD --checksum=sha256:d73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b \
    https://truststore.pki.rds.amazonaws.com/ap-southeast-2/ap-southeast-2-bundle.pem \
    /etc/ssl/certs/aws-rds-ap-southeast-2-bundle.pem

COPY backend/pyproject.toml .
COPY backend/uv.lock .

# Dev/staging builds pass --build-arg UV_SYNC_FLAGS="--extra dev" so the
# OpenAPI export tool (PyYAML) is available. Prod keeps the default
# --no-dev so optional tooling stays out of the runtime image.
ARG UV_SYNC_FLAGS="--no-dev"
RUN uv sync --frozen ${UV_SYNC_FLAGS}

COPY backend .

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "/app/scripts/healthcheck.py"]

CMD ["uv", "run", "gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
