FROM python:3.14-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# The nominal typing regression test invokes Pyright inside the test container.
COPY --from=node:24-trixie-slim /usr/local/bin/node /usr/local/bin/node

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/flowform/backend-test-venv \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 


WORKDIR /app

COPY backend/pyproject.toml .
COPY backend/uv.lock .

RUN uv sync --frozen --extra dev --extra test

COPY backend .

CMD ["/bin/bash"]
