"""Last-line-of-defence redaction for emitted log records."""

from __future__ import annotations

import copy
import logging
import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[REDACTED]"

_SENSITIVE_KEYS = frozenset(
    {
        "apikey",
        "accesskeyid",
        "authorization",
        "awsaccesskeyid",
        "awssecretaccesskey",
        "awssessiontoken",
        "clientsecret",
        "connectionstring",
        "cookie",
        "databaseurl",
        "idtoken",
        "linkagesecret",
        "password",
        "passwd",
        "privatekey",
        "providermessage",
        "proxyauthorization",
        "refreshtoken",
        "secret",
        "secretaccesskey",
        "secretstring",
        "sessiontoken",
        "setcookie",
        "token",
        "accesstoken",
        "wrappeddek",
    }
)

_SENSITIVE_KEY_PATTERN = (
    r"authorization|proxy[-_]?authorization|cookie|set[-_]?cookie|password|passwd|"
    r"(?:aws[-_]?)?secret[-_]?access[-_]?key|(?:aws[-_]?)?session[-_]?token|"
    r"(?:aws[-_]?)?access[-_]?key[-_]?id|"
    r"secret(?:string|_string)?|token|access[-_]?token|refresh[-_]?token|id[-_]?token|"
    r"client[-_]?secret|api[-_]?key|private[-_]?key|provider[-_]?message|database[-_]?url|"
    r"connection[-_]?string|wrapped[-_]?dek|linkage[-_]?secret"
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
    r"(?P<value>[^\s,;}\]]+)",
    re.IGNORECASE,
)
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_AWS_ACCESS_KEY_RE = re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")
_GITHUB_TOKEN_RE = re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")
_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?"
    r"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    re.DOTALL,
)

_STANDARD_LOG_RECORD_ATTRS = frozenset(
    {
        *logging.makeLogRecord({}).__dict__,
        "asctime",
        "message",
    }
)


def _normalise_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _is_sensitive_key(value: object) -> bool:
    return _normalise_key(value) in _SENSITIVE_KEYS


def redact_text(value: str) -> str:
    """Mask recognisable secret-bearing fragments while retaining log context."""
    redacted = _PRIVATE_KEY_RE.sub(REDACTED, value)
    redacted = _DATABASE_URL_RE.sub(lambda match: f"{match.group('prefix')}{REDACTED}", redacted)
    redacted = _BEARER_RE.sub(lambda match: f"{match.group('prefix')}{REDACTED}", redacted)
    redacted = _QUOTED_VALUE_RE.sub(
        lambda match: f"{match.group('prefix')}{match.group('quote')}{REDACTED}{match.group('quote')}",
        redacted,
    )
    redacted = _UNQUOTED_VALUE_RE.sub(
        lambda match: f"{match.group('prefix')}{REDACTED}",
        redacted,
    )
    redacted = _JWT_RE.sub(REDACTED, redacted)
    redacted = _AWS_ACCESS_KEY_RE.sub(REDACTED, redacted)
    return _GITHUB_TOKEN_RE.sub(REDACTED, redacted)


def _sanitize_value(value: Any, *, key: object | None = None, depth: int = 0) -> Any:
    if key is not None and _is_sensitive_key(key):
        return REDACTED
    if depth >= 10:
        return "[MAX_DEPTH]"
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, bytes):
        return redact_text(repr(value))
    if isinstance(value, Mapping):
        return {
            item_key: _sanitize_value(item_value, key=item_key, depth=depth + 1)
            for item_key, item_value in value.items()
        }
    if isinstance(value, tuple):
        return tuple(_sanitize_value(item, depth=depth + 1) for item in value)
    if isinstance(value, list):
        return [_sanitize_value(item, depth=depth + 1) for item in value]
    if isinstance(value, set):
        return {_sanitize_value(item, depth=depth + 1) for item in value}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_sanitize_value(item, depth=depth + 1) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
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
