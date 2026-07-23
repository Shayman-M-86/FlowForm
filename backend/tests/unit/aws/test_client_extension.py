from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest
from flask import Flask

from app.aws.client_extension import EXTENSION_KEY, AwsClientManager
from app.core.config import Settings
from app.core.errors import InitializationError


def test_startup_validation_failure_prevents_aws_extension_attachment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = Flask(__name__)
    app.extensions["settings"] = cast(
        Settings,
        SimpleNamespace(flowform=SimpleNamespace(aws=SimpleNamespace())),
    )
    manager = AwsClientManager()
    clients = [MagicMock(), MagicMock(), MagicMock()]
    monkeypatch.setattr(manager, "_build_client", MagicMock(side_effect=clients))
    validation = MagicMock(side_effect=InitializationError("probe failed"))
    monkeypatch.setattr("app.aws.client_extension.validate_aws_runtime_access", validation)

    with pytest.raises(InitializationError, match="probe failed"):
        manager.init_app(app)

    validation.assert_called_once()
    assert EXTENSION_KEY not in app.extensions
    with pytest.raises(RuntimeError, match="not initialized"):
        _ = manager.clients
