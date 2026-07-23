from flask import Flask

from app.core.config import CorsSettings
from app.core.extensions import init_cors


def test_allowed_origin_receives_credentialed_cors_headers() -> None:
    app = Flask(__name__)
    init_cors(app, CorsSettings(origins=["https://studio.example.test"]))

    @app.get("/api/example")
    def example():
        return "ok"

    response = app.test_client().get("/api/example", headers={"Origin": "https://studio.example.test"})
    assert response.headers["Access-Control-Allow-Origin"] == "https://studio.example.test"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"


def test_unapproved_origin_receives_no_cors_headers() -> None:
    app = Flask(__name__)
    init_cors(app, CorsSettings(origins=["https://studio.example.test"]))

    @app.get("/api/example")
    def example():
        return "ok"

    response = app.test_client().get("/api/example", headers={"Origin": "https://attacker.example.test"})
    assert "Access-Control-Allow-Origin" not in response.headers
