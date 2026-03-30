FROM python:3.14-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    WEB_CONCURRENCY=2 \
    TIMEOUT=60


WORKDIR /app

COPY backend/pyproject.toml .
COPY backend/uv.lock .
RUN uv sync --frozen --no-dev

COPY backend .

EXPOSE 5000

CMD ["uv", "run", "gunicorn", "-b", "0.0.0.0:5000", "wsgi:app"]