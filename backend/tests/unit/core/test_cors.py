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
    assert response.headers["Timing-Allow-Origin"] == "https://studio.example.test"


def test_unapproved_origin_receives_no_cors_headers() -> None:
    app = Flask(__name__)
    init_cors(app, CorsSettings(origins=["https://studio.example.test"]))

    @app.get("/api/example")
    def example():
        return "ok"

    response = app.test_client().get("/api/example", headers={"Origin": "https://attacker.example.test"})
    assert "Access-Control-Allow-Origin" not in response.headers
    assert "Timing-Allow-Origin" not in response.headers


def test_api_preflight_allows_browser_trace_context() -> None:
    app = Flask(__name__)
    init_cors(app, CorsSettings(origins=["https://studio.example.test"]))

    @app.get("/api/example")
    def example():
        return "ok"

    response = app.test_client().options(
        "/api/example",
        headers={
            "Origin": "https://studio.example.test",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,traceparent",
        },
    )
    assert response.headers["Access-Control-Allow-Origin"] == "https://studio.example.test"
    assert set(response.headers["Access-Control-Allow-Headers"].lower().split(", ")) == {
        "authorization",
        "traceparent",
    }
    assert response.headers["Access-Control-Max-Age"] == "7200"
