from __future__ import annotations

import logging
import stat
from types import SimpleNamespace
from typing import cast

from flask import Flask

from app.core.config import Settings
from app.logging.logging_config import setup_logging


def test_setup_logging_writes_exceptions_to_app_log(tmp_path) -> None:
    app_log = tmp_path / "app.log"
    app = Flask(__name__)
    settings = SimpleNamespace(
        flowform=SimpleNamespace(
            env="dev",
            server=SimpleNamespace(host="127.0.0.1", port=5000),
            logging=SimpleNamespace(
                level="DEBUG",
                log_json=False,
                sqlalchemy_level="WARNING",
                werkzeug_level="WARNING",
                log_file=str(app_log),
                log_file_max_bytes=1024 * 1024,
                log_file_backup_count=1,
                requests=False,
                duration=False,
            ),
        )
    )

    setup_logging(app, cast(Settings, settings))

    logger = logging.getLogger("app.tests.logging")
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        logger.exception("expected failure")

    for handler in logging.getLogger().handlers:
        handler.flush()

    assert "RuntimeError: boom" in app_log.read_text(encoding="utf-8")
    assert stat.S_IMODE(app_log.stat().st_mode) == 0o600
    assert not (tmp_path / "error.log").exists()
