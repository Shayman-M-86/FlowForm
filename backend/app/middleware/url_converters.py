"""Custom Werkzeug URL converters with explicit bounds.

These exist so path segments reject impossible values at the routing layer
instead of forwarding oversized values to handlers. The converters pair
runtime ``regex`` values with attributes that the OpenAPI spec builder reads
to emit matching constraints on the corresponding path parameter.

Usage in a route:

    @bp.route("/<bint:project_id>", methods=["GET"])
    def get_project(project_id: int): ...

    @bp.route("/surveys/<public_slug:public_slug>", methods=["GET"])
    def get_public_survey(public_slug: str): ...

Register via :func:`register_url_converters` during app construction so the
converters are available before any blueprints attach their routes.
"""

from __future__ import annotations

from flask import Flask
from werkzeug.routing import BaseConverter, ValidationError

from app.schema.api import limits


class _BoundedStringConverter(BaseConverter):
    """Base class for length-capped string path converters."""

    MAX_LENGTH: int = 0  # subclasses override

    def __init__(self, url_map, *args, **kwargs) -> None:
        super().__init__(url_map, *args, **kwargs)
        self.regex = rf"[^/]{{1,{self.MAX_LENGTH}}}"


class PublicSlugConverter(_BoundedStringConverter):
    """Path converter for public survey slugs."""

    MAX_LENGTH = limits.SLUG_MAX


class BoundedIntegerConverter(BaseConverter):
    """Integer path converter with an explicit positive upper bound.

    Werkzeug's built-in ``int`` converter parses any non-negative integer
    with no ceiling, so a 50-digit value still flows into the handler.
    This converter:

    - Rejects negative / zero values (resource ids are 1-indexed serials).
    - Rejects anything that doesn't fit in PostgreSQL ``INTEGER``.
    - Advertises ``MIN_VALUE`` / ``MAX_VALUE`` so the OpenAPI spec builder
      emits ``minimum`` / ``maximum`` on the path parameter automatically.

    Pairs with :data:`limits.INT_ID_MIN` / :data:`limits.INT_ID_MAX`.
    """

    MIN_VALUE: int = limits.INT_ID_MIN
    MAX_VALUE: int = limits.INT_ID_MAX

    def __init__(self, url_map, *args, **kwargs) -> None:
        super().__init__(url_map, *args, **kwargs)
        # Cap the number of digits so we never even parse outlier values.
        # 10 digits is enough for 2^31 - 1 (2,147,483,647).
        max_digits = len(str(self.MAX_VALUE))
        self.regex = rf"\d{{1,{max_digits}}}"

    def to_python(self, value: str) -> int:
        parsed = int(value)
        if parsed < self.MIN_VALUE or parsed > self.MAX_VALUE:
            # Raising ValidationError makes Werkzeug treat the URL as a
            # non-match and continues looking for other routes (eventually
            # 404'ing) instead of surfacing a 500.
            raise ValidationError()
        return parsed

    def to_url(self, value: int) -> str:
        return str(value)


# Converters keyed by the name used in Flask route templates
# (``<public_slug:public_slug>`` → ``PublicSlugConverter``;
# ``<bint:survey_id>`` → ``BoundedIntegerConverter``).
URL_CONVERTERS: dict[str, type[BaseConverter]] = {
    "public_slug": PublicSlugConverter,
    "bint": BoundedIntegerConverter,
}


def register_url_converters(app: Flask) -> None:
    """Attach the custom URL converters to ``app.url_map``."""
    for name, converter_cls in URL_CONVERTERS.items():
        app.url_map.converters[name] = converter_cls
