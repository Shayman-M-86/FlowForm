from __future__ import annotations

import json
import logging
import stat
from types import SimpleNamespace
from typing import cast

from flask import Flask

from app.core.config import Settings
from app.logging.logging_config import JsonFormatter, log_startup, setup_logging


def _make_record(level: int = logging.INFO, **extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="app.http",
        level=level,
        pathname=__file__,
        lineno=1,
        msg="request done",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_emits_canonical_schema() -> None:
    record = _make_record(
        level=logging.ERROR,
        status_code=502,
        remote_addr="192.0.2.1",
        method="POST",
        path="/api/v1/account/change-password",
        request_id="req-123",
    )

    payload = json.loads(JsonFormatter().format(record))

    # level is lowercase to align with caddy/squid across the log suite.
    assert payload["level"] == "error"
    # Canonical field names: status (not status_code), client_ip (not remote_addr).
    assert payload["status"] == 502
    assert payload["client_ip"] == "192.0.2.1"
    assert "status_code" not in payload
    assert "remote_addr" not in payload
    assert payload["method"] == "POST"
    assert payload["path"] == "/api/v1/account/change-password"
    assert payload["message"] == "request done"


def test_json_formatter_omits_absent_optional_fields() -> None:
    payload = json.loads(JsonFormatter().format(_make_record()))

    assert payload["level"] == "info"
    for absent in ("status", "client_ip", "request_id", "duration_ms"):
        assert absent not in payload


def test_json_formatter_emits_startup_environment_field() -> None:
    record = _make_record(
        level=logging.INFO,
        event_type="app_startup",
        environment="prod",
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event_type"] == "app_startup"
    assert payload["environment"] == "prod"


def _startup_settings(env: str = "prod") -> SimpleNamespace:
    return SimpleNamespace(
        flowform=SimpleNamespace(
            env=env,
            app=SimpleNamespace(version="9.9.9"),
            server=SimpleNamespace(host="0.0.0.0", port=5000),
        )
    )


def test_log_startup_emits_success_and_environment_at_info(monkeypatch, caplog) -> None:
    # Gunicorn sets no WERKZEUG_RUN_MAIN marker; the banner must still emit.
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    app = Flask(__name__)

    with caplog.at_level(logging.INFO, logger="app.startup"):
        log_startup(app, cast(Settings, _startup_settings(env="prod")))

    records = [r for r in caplog.records if r.name == "app.startup"]
    assert len(records) == 2
    assert all(r.levelno == logging.INFO for r in records)
    assert any("started successfully" in r.getMessage() for r in records)
    env_record = next(r for r in records if "environment" in r.getMessage())
    assert env_record.environment == "prod"
    assert env_record.event_type == "app_startup"


def test_log_startup_skips_werkzeug_reloader_parent(monkeypatch, caplog) -> None:
    # The Flask dev reloader's parent process has WERKZEUG_RUN_MAIN unset-to-false;
    # only the child (WERKZEUG_RUN_MAIN=true) serves, so the parent must stay quiet.
    monkeypatch.setenv("WERKZEUG_RUN_MAIN", "")
    app = Flask(__name__)

    with caplog.at_level(logging.INFO, logger="app.startup"):
        log_startup(app, cast(Settings, _startup_settings(env="dev")))

    assert [r for r in caplog.records if r.name == "app.startup"] == []


def test_setup_logging_writes_exceptions_to_app_log(tmp_path) -> None:
    app_log = tmp_path / "app.log"
    app = Flask(__name__)
    settings = SimpleNamespace(
        flowform=SimpleNamespace(
            env="dev",
            app=SimpleNamespace(version="9.9.9"),
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
