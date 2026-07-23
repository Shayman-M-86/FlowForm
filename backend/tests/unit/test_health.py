from flask import Flask

from app.api.v1.system import health as health_module
from app.api.v1.system import system_bp


def test_health_response_includes_project_version() -> None:
    app = Flask(__name__)
    app.config["APP_VERSION"] = "1.2.3"

    with app.app_context():
        response, status_code = health_module.health_check()

    assert status_code == 200
    assert response.get_json()["data"]["version"] == "1.2.3"


def test_readiness_response_includes_project_version(monkeypatch) -> None:
    app = Flask(__name__)
    app.config["APP_VERSION"] = "1.2.3"
    monkeypatch.setattr(health_module, "db_check", lambda: ("Service is ready", 200))

    with app.app_context():
        response, status_code = health_module.readiness_check()

    assert status_code == 200
    assert response.get_json()["data"]["version"] == "1.2.3"


def test_readiness_database_probes_are_cached_for_ten_seconds(monkeypatch) -> None:
    class FakeDb:
        def __init__(self) -> None:
            self.probe_count = 0

        def execute(self, _query: object) -> None:
            self.probe_count += 1

    core_db = FakeDb()
    response_db = FakeDb()
    times = iter((0.0, 0.0, 5.0, 10.0, 10.0))

    monkeypatch.setattr(health_module, "_readiness_cache", None)
    monkeypatch.setattr(health_module, "monotonic", lambda: next(times))
    monkeypatch.setattr(health_module, "get_core_db", lambda: core_db)
    monkeypatch.setattr(health_module, "get_response_db", lambda: response_db)

    assert health_module.db_check() == ("Service is ready", 200)
    assert health_module.db_check() == ("Service is ready", 200)
    assert health_module.db_check() == ("Service is ready", 200)

    assert core_db.probe_count == 2
    assert response_db.probe_count == 2


def test_removed_test_email_route_returns_not_found() -> None:
    app = Flask(__name__)
    app.register_blueprint(system_bp, url_prefix="/api/v1/system")

    assert app.test_client().post("/api/v1/system/health/test-email").status_code == 404
