"""Application entry point; importing contracts does not initialize runtime services."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask import Flask

    from app.core.config import Settings

__all__ = ["create_app"]


def create_app(*, settings: Settings | None = None, flask_config: Mapping[str, Any] | None = None) -> Flask:
    """Load the runtime factory only when an application is requested."""
    from app.core.factory import create_app as factory

    return factory(settings=settings, flask_config=flask_config)
