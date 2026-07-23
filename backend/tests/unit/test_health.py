from flask import Flask

from app.api.v1.system import health as health_module


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
