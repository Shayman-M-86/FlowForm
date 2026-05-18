from flask import Flask

from app.openapi.spec import build_spec


def test_openapi_spec_uses_version_3_2_0() -> None:
    document = build_spec(Flask(__name__))

    assert document["openapi"] == "3.2.0"
