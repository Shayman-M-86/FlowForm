from typing import Any

from flask import Request
from pydantic import BaseModel, ValidationError
from werkzeug.exceptions import BadRequest, UnsupportedMediaType


def _get_json_object(request_obj: Request) -> dict[str, Any]:
    """Parse the request body as a JSON object.

    Raises:
        UnsupportedMediaType: The request body is not JSON.
        BadRequest: The JSON is malformed or the decoded body is not an object.
    """
    if not request_obj.is_json:
        raise UnsupportedMediaType("Request body must be JSON")

    body = request_obj.get_json()

    if not isinstance(body, dict):
        raise BadRequest("JSON body must be an object")

    return body


def parse[TModel: BaseModel](model_cls: type[TModel], request_obj: Request) -> TModel:
    """Parse the JSON request body into a Pydantic model.

    Raises:
        HTTPException: If the request body is invalid for the endpoint.
        ValidationError: If the JSON body does not satisfy the Pydantic model schema.
    """
    body = _get_json_object(request_obj)
    return model_cls.model_validate(body)


def parse_query[TModel: BaseModel](model_cls: type[TModel], request_obj: Request) -> TModel:
    """Parse the query string into a Pydantic model."""
    return model_cls.model_validate(request_obj.args.to_dict())


# Fields whose Python name differs from their JSON alias.
_ALIAS_MAP = {"schema_": "schema"}


# Discriminator values injected by Pydantic into error locs for discriminated unions.
# These are never present in the request JSON and should be stripped from field paths.
_UNION_TAGS: frozenset[str] = frozenset({"choice", "field", "matching", "rating"})


def _loc_to_field(loc: tuple) -> str:
    """Convert a Pydantic error loc tuple to a dot-separated JSON field path.

    Pydantic discriminated union errors inject the matched discriminator value
    (e.g. ``"choice"``) as an extra segment into the loc. We strip known
    discriminator values so the path reflects the actual request JSON structure.
    """
    cleaned = [part for part in loc if part not in _UNION_TAGS]
    return ".".join(_ALIAS_MAP.get(str(p), str(p)) for p in cleaned)


_PYDANTIC_MSG_PREFIXES = ("Value error, ", "Assertion failed, ")


def _clean_message(msg: str) -> str:
    """Strip Pydantic internal prefixes from validator messages."""
    for prefix in _PYDANTIC_MSG_PREFIXES:
        if msg.startswith(prefix):
            return msg[len(prefix):]
    return msg


def normalize_pydantic_errors(exc: ValidationError) -> list[dict[str, object]]:
    """Convert Pydantic validation errors into a consistent format for API responses."""
    return [
        {
            "field": _loc_to_field(err.get("loc", ())),
            "message": _clean_message(err.get("msg", "")),
            "type": err.get("type"),
        }
        for err in exc.errors(include_url=False)
    ]
