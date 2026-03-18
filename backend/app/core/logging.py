from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return json.dumps(payload)


def get_formatter(json_logs: bool) -> logging.Formatter:
    if json_logs:
        return JsonFormatter()
    return logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def build_stream_handler(
    *,
    json_logs: bool,
    stream: Any = sys.stdout,
) -> logging.Handler:
    handler = logging.StreamHandler(stream)
    handler.setFormatter(get_formatter(json_logs))
    return handler


def build_file_handler(
    *,
    path: str | Path,
    json_logs: bool,
    encoding: str = "utf-8",
) -> logging.Handler:
    handler = logging.FileHandler(path, encoding=encoding)
    handler.setFormatter(get_formatter(json_logs))
    return handler


def configure_root_logger(
    *,
    level: str = "INFO",
    handlers: list[logging.Handler] | None = None,
    sqlalchemy_level: str = "WARNING",
    werkzeug_level: str = "INFO",
) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    for handler in handlers or []:
        root.addHandler(handler)

    logging.getLogger("sqlalchemy.engine").setLevel(
        getattr(logging, sqlalchemy_level.upper(), logging.WARNING)
    )
    logging.getLogger("werkzeug").setLevel(
        getattr(logging, werkzeug_level.upper(), logging.INFO)
    )


def setup_logging(settings: Settings) -> None:
    """
    Expects settings.logging with fields like:
      - level
      - json
      - sqlalchemy_level (optional)
      - werkzeug_level (optional)
      - log_file (optional)
    """
    json_logs = settings.logging.log_json
    handlers: list[logging.Handler] = [
        build_stream_handler(json_logs=json_logs, stream=sys.stdout),
    ]

    log_file = getattr(settings.logging, "log_file", None)
    if log_file:
        handlers.append(
            build_file_handler(
                path=log_file,
                json_logs=json_logs,
            )
        )

    configure_root_logger(
        level=settings.logging.level,
        handlers=handlers,
        sqlalchemy_level=getattr(settings.logging, "sqlalchemy_level", "WARNING"),
        werkzeug_level=getattr(settings.logging, "werkzeug_level", "INFO"),
    )


def setup_bootstrap_logging() -> None:
    configure_root_logger(
        level="INFO",
        handlers=[
            build_stream_handler(json_logs=False, stream=sys.stderr),
        ],
    )
