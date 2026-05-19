import pytest  # type: ignore[import]
from flask import Flask
from pydantic import BaseModel

from app.openapi import openapi_route
from app.openapi.registry import clear_registry
from app.openapi.spec import build_spec


@pytest.fixture(autouse=True)
def clean_openapi_registry():
    clear_registry()
    yield
    clear_registry()


def test_openapi_spec_uses_version_3_2_0() -> None:
    document = build_spec(Flask(__name__))

    assert document["openapi"] == "3.2.0"


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
