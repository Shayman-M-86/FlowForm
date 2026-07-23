"""Last-line-of-defence sanitization for emitted log records."""

from __future__ import annotations

import copy
import logging
import re
from collections.abc import Mapping
from typing import Any

from pydantic import SecretBytes, SecretStr

REDACTED = "[REDACTED]"
_MAX_DEPTH = 10

# Keep one vocabulary for both structured keys and key/value text fragments.
# Separators and casing are ignored, so ``client-secret``, ``client_secret``,
# and ``ClientSecret`` all share the same rule.
_SENSITIVE_KEY_NAMES = """
    access_key_id access_token api_key authorization
    aws_access_key_id aws_secret_access_key aws_session_token
    client_secret connection_string cookie database_url id_token linkage_secret
    password passwd private_key provider_message proxy_authorization refresh_token
    secret secret_access_key secret_string session_token set_cookie token wrapped_dek
""".split()  # noqa: SIM905 - grouped names are easier to audit than a 26-line literal


def _normalise_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


_SENSITIVE_KEYS = frozenset(_normalise_key(name) for name in _SENSITIVE_KEY_NAMES)


def _text_key_pattern(name: str) -> str:
    """Allow common separators, including no separator, between key words."""
    return r"[-_ ]*".join(re.escape(word) for word in name.split("_"))


_SENSITIVE_KEY_PATTERN = "|".join(
    _text_key_pattern(name) for name in sorted(_SENSITIVE_KEY_NAMES, key=len, reverse=True)
)

_DATABASE_URL_RE = re.compile(
    r"(?P<prefix>[a-z][a-z0-9+.-]*://[^:/@\s]+:)(?P<value>[^@/\s]+)(?=@)",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"(?P<prefix>\bBearer\s+)[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_QUOTED_VALUE_RE = re.compile(
    rf"(?P<prefix>['\"]?(?:{_SENSITIVE_KEY_PATTERN})['\"]?\s*[:=]\s*)"
    r"(?P<quote>['\"])(?:\\.|(?!\2).)*?(?P=quote)",
    re.IGNORECASE,
)
_UNQUOTED_VALUE_RE = re.compile(
    rf"(?P<prefix>\b(?:{_SENSITIVE_KEY_PATTERN})\b\s*[:=]\s*)"
    rf"(?P<value>{re.escape(REDACTED)}|[^\s,;}}\]]+)",
    re.IGNORECASE,
)
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_AWS_ACCESS_KEY_RE = re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")
_GITHUB_TOKEN_RE = re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")
_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN (?P<key_type>(?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY)-----.*?"
    r"-----END (?P=key_type)-----",
    re.DOTALL,
)


def _redacted_match(match: re.Match[str]) -> str:
    """Retain useful syntax around a matched secret."""
    groups = match.groupdict()
    quote = groups.get("quote", "")
    return f"{groups.get('prefix', '')}{quote}{REDACTED}{quote}"


_STANDARD_LOG_RECORD_ATTRS = frozenset((*logging.makeLogRecord({}).__dict__, "asctime", "message"))


def _is_sensitive_key(value: object) -> bool:
    return _normalise_key(value) in _SENSITIVE_KEYS


def redact_text(value: str) -> str:
    """Mask recognisable secret-bearing fragments while retaining log context."""
    value = _PRIVATE_KEY_RE.sub(REDACTED, value)
    for pattern in (_DATABASE_URL_RE, _BEARER_RE, _QUOTED_VALUE_RE, _UNQUOTED_VALUE_RE):
        value = pattern.sub(_redacted_match, value)
    for pattern in (_JWT_RE, _AWS_ACCESS_KEY_RE, _GITHUB_TOKEN_RE):
        value = pattern.sub(REDACTED, value)
    return value


def _sanitize_value(value: Any, *, key: object | None = None, depth: int = 0) -> Any:
    """Sanitize a value destined for a structured log field."""
    if key is not None and _is_sensitive_key(key):
        return REDACTED
    if depth >= _MAX_DEPTH:
        return "[MAX_DEPTH]"

    match value:
        case SecretStr() | SecretBytes():
            return REDACTED
        case str():
            return redact_text(value)
        case bytes() | bytearray():
            return redact_text(bytes(value).decode(errors="replace"))
        case Mapping():
            return {
                item_key: _sanitize_value(item_value, key=item_key, depth=depth + 1)
                for item_key, item_value in value.items()
            }
        case list() | tuple() | set() | frozenset():
            return [_sanitize_value(item, depth=depth + 1) for item in value]
        case None | bool() | int() | float():
            return value
        case _:
            return redact_text(str(value))


class SensitiveDataFilter(logging.Filter):
    """Return a sanitized copy of every record immediately before emission."""

    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        sanitized = copy.copy(record)
        sanitized.msg = redact_text(record.getMessage())
        sanitized.args = ()

        for attr, value in record.__dict__.items():
            if attr in _STANDARD_LOG_RECORD_ATTRS:
                continue
            setattr(sanitized, attr, _sanitize_value(value, key=attr))

        if record.exc_info:
            exception_text = logging.Formatter().formatException(record.exc_info)
            sanitized.exc_text = redact_text(exception_text)
        elif record.exc_text:
            sanitized.exc_text = redact_text(record.exc_text)

        if record.stack_info:
            sanitized.stack_info = redact_text(record.stack_info)
        if hasattr(record, "message"):
            sanitized.message = redact_text(str(record.message))

        return sanitized


def install_sensitive_data_filter(handler: logging.Handler) -> None:
    """Ensure one sensitive-data filter protects an output handler."""
    if any(isinstance(item, SensitiveDataFilter) for item in handler.filters):
        return
    handler.addFilter(SensitiveDataFilter())


def protect_root_handlers() -> None:
    """Protect every currently registered root handler, including pytest handlers."""
    for handler in logging.getLogger().handlers:
        install_sensitive_data_filter(handler)
