"""Script for writing the OpenAPI spec to disk as YAML.

Run from the backend directory:

    uv run python -m app.openapi.export
    uv run python -m app.openapi.export --output /tmp/snapshot.yaml
    uv run python -m app.openapi.export --check    # CI/pre-commit drift check

The export builds a fresh, minimal Flask app rather than reusing the
full ``create_app()`` factory — the spec only needs route registration,
so DB sessions, logging handlers, and rate limiting can be skipped. That
keeps the command fast and avoids needing a real config to regenerate
the spec from CI or a pre-commit hook.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml
from flask import Flask

from app.openapi.spec import build_spec

# Default location: backend/openapi.yaml — the parent of the ``app/`` package.
_DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "openapi.yaml"


_TOP_LEVEL_KEY_ORDER = (
    "openapi",
    "info",
    "servers",
    "security",
    "tags",
    "paths",
    "webhooks",
    "components",
)


def _reorder_top_level(spec: dict) -> dict:
    """Return a copy of the spec with top-level keys in the canonical order.

    Tools and humans expect ``openapi`` and ``info`` at the top of the file.
    The builder currently produces them in dict-insertion order, which puts
    ``info`` and ``paths`` first.
    """
    ordered: dict = {key: spec[key] for key in _TOP_LEVEL_KEY_ORDER if key in spec}
    for key, value in spec.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def _dump_yaml(spec: dict) -> str:
    """Serialize the spec dict to YAML with deterministic key ordering."""
    return yaml.safe_dump(
        _reorder_top_level(spec),
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=120,
    )


def _build_minimal_spec_app() -> Flask:
    """Build a Flask app with only what the spec builder needs.

    Skips DB sessions, logging file handlers, rate limiting, and seed data
    so the exporter can run from a clean checkout without any runtime
    config — useful for CI and pre-commit. The import is late-bound to
    avoid the circular import between ``app.api.v1`` (which uses
    ``@openapi_route``) and ``app.openapi`` (which registers this command).
    """
    from app.api.v1 import register_api_v1
    from app.middleware.url_converters import register_url_converters

    app = Flask("flowform-openapi-export")
    # Custom URL converters must attach to ``url_map`` before any route
    # references them, otherwise ``register_api_v1`` raises LookupError.
    register_url_converters(app)
    register_api_v1(app)
    return app


@click.command("openapi-export")
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=_DEFAULT_OUTPUT,
    show_default=True,
    help="Path to write the OpenAPI YAML file.",
)
@click.option(
    "--check",
    is_flag=True,
    help="Exit non-zero if the on-disk file differs from the generated spec.",
)
def openapi_export_command(output: Path, check: bool) -> None:
    """Write the OpenAPI spec to disk as YAML."""
    spec = build_spec(_build_minimal_spec_app())
    rendered = _dump_yaml(spec)

    if check:
        if not output.exists():
            click.echo(f"{output} does not exist.", err=True)
            sys.exit(1)
        existing = output.read_text(encoding="utf-8")
        if existing != rendered:
            click.echo(
                f"{output} is out of date. Run `flask openapi-export` to regenerate.",
                err=True,
            )
            sys.exit(1)
        click.echo(f"{output} is up to date.")
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    click.echo(f"Wrote OpenAPI spec to {output} ({len(rendered):,} bytes).")


def register_openapi_cli(app: Flask) -> None:
    """Attach the ``openapi-export`` Click command to the Flask app.

    Kept for parity with the rest of the CLI surface, but ``python -m
    app.openapi.export`` is the preferred entry point since it skips the
    heavy app factory.
    """
    app.cli.add_command(openapi_export_command)


if __name__ == "__main__":
    openapi_export_command()
