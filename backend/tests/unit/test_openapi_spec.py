import pytest  # type: ignore[import]
from flask import Flask
from pydantic import BaseModel

from app.openapi import openapi_route
from app.openapi.registry import clear_registry
from app.openapi.spec import build_spec, register_openapi_blueprint


@pytest.fixture(autouse=True)
def clean_openapi_registry():
    clear_registry()
    yield
    clear_registry()


def test_openapi_spec_uses_version_3_1_1() -> None:
    document = build_spec(Flask(__name__))

    assert document["openapi"] == "3.1.1"


def test_openapi_route_derives_method_and_path_from_flask_rule() -> None:
    clear_registry()
    app = Flask(__name__)

    @openapi_route(summary="Get widget", tags=["Widgets"])
    @app.route("/widgets/<int:widget_id>", methods=["GET"])
    def get_widget(widget_id: int):  # pragma: no cover
        return {"id": widget_id}

    document = build_spec(app)

    assert "/widgets/{widget_id}" in document["paths"]
    operation = document["paths"]["/widgets/{widget_id}"]["get"]
    assert operation["summary"] == "Get widget"
    assert operation["parameters"] == [
        {
            "name": "widget_id",
            "in": "path",
            "required": True,
            "schema": {"type": "integer"},
        }
    ]


def test_openapi_route_still_accepts_explicit_method_and_path() -> None:
    app = Flask(__name__)

    @openapi_route(method="POST", path="/widgets", summary="Create widget")
    def create_widget():  # pragma: no cover
        return {}, 201

    document = build_spec(app)

    assert document["paths"]["/widgets"]["post"]["summary"] == "Create widget"


def test_openapi_route_supports_array_response_models() -> None:
    class WidgetOut(BaseModel):
        id: int

    app = Flask(__name__)

    @openapi_route(summary="List widgets", response_model=list[WidgetOut])
    @app.route("/widgets", methods=["GET"])
    def list_widgets():  # pragma: no cover
        return []

    document = build_spec(app)

    schema = document["paths"]["/widgets"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema == {
        "type": "array",
        "items": {"$ref": "#/components/schemas/WidgetOut"},
    }


def test_openapi_route_can_disable_auth_requirement() -> None:
    app = Flask(__name__)

    @openapi_route(summary="Public widgets", auth="none")
    @app.route("/widgets", methods=["GET"])
    def public_widgets():  # pragma: no cover
        return []

    document = build_spec(app)

    assert document["security"] == [{"BearerAuth": []}]
    assert document["paths"]["/widgets"]["get"]["security"] == []


def test_openapi_route_can_make_auth_optional() -> None:
    app = Flask(__name__)

    @openapi_route(summary="Optional auth widgets", auth="optional")
    @app.route("/widgets", methods=["GET"])
    def optional_auth_widgets():  # pragma: no cover
        return []

    document = build_spec(app)

    assert document["security"] == [{"BearerAuth": []}]
    assert document["paths"]["/widgets"]["get"]["security"] == [{}, {"BearerAuth": []}]


def test_openapi_spec_uses_auth0_oauth_when_configured() -> None:
    app = Flask(__name__)
    app.config.update(
        AUTH0_DOMAIN="flowform.eu.auth0.com",
        AUTH0_AUDIENCE="https://api.flowform.example",
        AUTH0_CLIENT_ID="docs-client-id",
    )

    document = build_spec(app)

    assert document["security"] == [{"Auth0OAuth": []}]
    security_schemes = document["components"]["securitySchemes"]
    assert "BearerAuth" not in security_schemes
    assert security_schemes["Auth0OAuth"] == {
        "type": "oauth2",
        "description": "Log in with Auth0 to get an access token for this API.",
        "flows": {
            "authorizationCode": {
                "authorizationUrl": (
                    "https://flowform.eu.auth0.com/authorize?"
                    "audience=https%3A%2F%2Fapi.flowform.example"
                ),
                "tokenUrl": "https://flowform.eu.auth0.com/oauth/token",
                "scopes": {},
            }
        },
    }


def test_optional_auth_uses_auth0_oauth_when_configured() -> None:
    app = Flask(__name__)
    app.config.update(
        AUTH0_DOMAIN="flowform.eu.auth0.com",
        AUTH0_AUDIENCE="flowform-api",
        AUTH0_CLIENT_ID="docs-client-id",
    )

    @openapi_route(summary="Optional auth widgets", auth="optional")
    @app.route("/widgets", methods=["GET"])
    def optional_auth_widgets():  # pragma: no cover
        return []

    document = build_spec(app)

    assert document["paths"]["/widgets"]["get"]["security"] == [{}, {"Auth0OAuth": []}]


def test_swagger_ui_initializes_auth0_oauth() -> None:
    app = Flask(__name__)
    app.config["AUTH0_CLIENT_ID"] = "docs-client-id"
    register_openapi_blueprint(app)

    response = app.test_client().get("/api/v1/docs")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'oauth2RedirectUrl: window.location.origin + "/api/v1/docs/oauth2-redirect"' in html
    assert 'clientId: "docs-client-id"' in html
    assert "usePkceWithAuthorizationCodeGrant: true" in html


def test_swagger_ui_serves_oauth_redirect_page() -> None:
    app = Flask(__name__)
    register_openapi_blueprint(app)

    response = app.test_client().get("/api/v1/docs/oauth2-redirect")

    assert response.status_code == 200
    assert "swaggerUIRedirectOauth2" in response.get_data(as_text=True)


def test_register_openapi_blueprint_exposes_openapi_json() -> None:
    """Smoke-test that /openapi.json is served when the blueprint is registered.

    Whether the blueprint gets registered at all is the caller's decision —
    see ``app.core.register_options.openapi_register_options``, which only
    invokes this in non-prod environments.
    """
    app = Flask(__name__)
    register_openapi_blueprint(app)

    response = app.test_client().get("/openapi.json")

    assert response.status_code == 200
    assert response.is_json
    assert response.get_json()["openapi"] == "3.1.1"


def test_openapi_route_emits_query_model_parameters() -> None:
    class WidgetQuery(BaseModel):
        token: str
        page: int = 1

    app = Flask(__name__)

    @openapi_route(summary="Resolve widget", query_model=WidgetQuery)
    @app.route("/widgets/resolve", methods=["GET"])
    def resolve_widget():  # pragma: no cover
        return {}

    document = build_spec(app)

    parameters = document["paths"]["/widgets/resolve"]["get"]["parameters"]
    assert parameters == [
        {
            "name": "token",
            "in": "query",
            "required": True,
            "schema": {"title": "Token", "type": "string"},
        },
        {
            "name": "page",
            "in": "query",
            "required": False,
            "schema": {"default": 1, "title": "Page", "type": "integer"},
        },
    ]


def test_operation_id_is_derived_from_handler_function_name() -> None:
    app = Flask(__name__)

    @openapi_route(summary="List widgets", tags=["Widgets"])
    @app.route("/widgets", methods=["GET"])
    def list_widgets():  # pragma: no cover
        return []

    @openapi_route(summary="Get widget", tags=["Widgets"])
    @app.route("/widgets/<int:widget_id>", methods=["GET"])
    def get_widget(widget_id: int):  # pragma: no cover
        return {"id": widget_id}

    document = build_spec(app)

    assert document["paths"]["/widgets"]["get"]["operationId"] == "listWidgets"
    assert document["paths"]["/widgets/{widget_id}"]["get"]["operationId"] == "getWidget"


def test_operation_ids_are_unique_across_the_document() -> None:
    app = Flask(__name__)

    @openapi_route(summary="Create widget", tags=["Widgets"])
    @app.route("/widgets", methods=["POST"])
    def create_widget():  # pragma: no cover
        return {}, 201

    @openapi_route(summary="Delete widget", tags=["Widgets"])
    @app.route("/widgets/<int:widget_id>", methods=["DELETE"])
    def delete_widget(widget_id: int):  # pragma: no cover
        return "", 204

    document = build_spec(app)

    seen: list[str] = []
    for path_item in document["paths"].values():
        for operation in path_item.values():
            if isinstance(operation, dict) and "operationId" in operation:
                seen.append(operation["operationId"])

    assert seen, "expected at least one operationId in the document"
    assert len(seen) == len(set(seen)), f"duplicate operationIds: {seen}"


def test_info_version_defaults_to_pyproject_version() -> None:
    import tomllib
    from pathlib import Path

    pyproject_version = tomllib.loads(
        (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text()
    )["project"]["version"]

    document = build_spec(Flask(__name__))

    assert document["info"]["version"] == pyproject_version


def test_info_version_can_be_overridden_via_config() -> None:
    app = Flask(__name__)
    app.config["OPENAPI_VERSION"] = "2.5.1"

    document = build_spec(app)

    assert document["info"]["version"] == "2.5.1"


def test_servers_block_falls_back_to_localhost() -> None:
    document = build_spec(Flask(__name__))

    assert document["servers"] == [
        {"url": "http://localhost:5000", "description": "Local development"}
    ]


def test_servers_block_respects_configured_list() -> None:
    app = Flask(__name__)
    app.config["OPENAPI_SERVERS"] = [
        {"url": "https://api.flowform.example", "description": "Production"},
        {"url": "https://staging.api.flowform.example", "description": "Staging"},
    ]

    document = build_spec(app)

    assert document["servers"] == [
        {"url": "https://api.flowform.example", "description": "Production"},
        {"url": "https://staging.api.flowform.example", "description": "Staging"},
    ]


def test_servers_block_respects_single_url_override() -> None:
    app = Flask(__name__)
    app.config["OPENAPI_SERVER_URL"] = "https://api.flowform.example"
    app.config["OPENAPI_SERVER_DESCRIPTION"] = "Production"

    document = build_spec(app)

    assert document["servers"] == [
        {"url": "https://api.flowform.example", "description": "Production"}
    ]
