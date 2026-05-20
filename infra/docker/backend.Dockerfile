FROM python:3.14-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/flowform/backend-venv \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    WEB_CONCURRENCY=2 \
    TIMEOUT=60


WORKDIR /app

COPY backend/pyproject.toml .
COPY backend/uv.lock .

# Dev/staging builds pass --build-arg UV_SYNC_FLAGS="--extra dev" so the
# OpenAPI export tool (PyYAML) is available. Prod keeps the default
# --no-dev so optional tooling stays out of the runtime image.
ARG UV_SYNC_FLAGS="--no-dev"
RUN uv sync --frozen ${UV_SYNC_FLAGS}

COPY backend .

EXPOSE 5000

CMD ["uv", "run", "gunicorn", "-b", "0.0.0.0:5000", "wsgi:app"]