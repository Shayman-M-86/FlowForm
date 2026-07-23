from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from app.aws.startup_validation import validate_aws_runtime_access
from app.core.config import Settings
from app.core.errors import InitializationError


def _settings(environment: str = "dev") -> Settings:
    return cast(
        Settings,
        SimpleNamespace(
            flowform=SimpleNamespace(
                env=environment,
                encryption=SimpleNamespace(
                    kms_key_arn="arn:aws:kms:ap-southeast-2:123456789012:key/test",
                    linkage_secret_arn=("arn:aws:secretsmanager:ap-southeast-2:123456789012:secret:test"),
                ),
            )
        ),
    )


def _clients() -> Any:
    clients = SimpleNamespace(kms=MagicMock(), secretsmanager=MagicMock())
    clients.secretsmanager.get_secret_value.return_value = {"SecretString": "available"}
    clients.kms.encrypt.return_value = {"CiphertextBlob": b"ciphertext"}
    return clients


def test_test_environment_skips_aws_startup_calls() -> None:
    clients = _clients()

    validate_aws_runtime_access(settings=_settings("test"), clients=clients)

    clients.secretsmanager.get_secret_value.assert_not_called()
    clients.kms.encrypt.assert_not_called()
    clients.kms.decrypt.assert_not_called()


def test_dev_environment_proves_secret_read_and_kms_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clients = _clients()
    probe = b"known-startup-probe"
    monkeypatch.setattr(
        "app.aws.startup_validation.secrets.token_bytes",
        MagicMock(return_value=probe),
    )
    clients.kms.decrypt.return_value = {"Plaintext": probe}

    validate_aws_runtime_access(settings=_settings(), clients=clients)

    clients.secretsmanager.get_secret_value.assert_called_once_with(
        SecretId="arn:aws:secretsmanager:ap-southeast-2:123456789012:secret:test",
        VersionStage="AWSCURRENT",
    )
    clients.kms.encrypt.assert_called_once()
    clients.kms.decrypt.assert_called_once_with(
        KeyId="arn:aws:kms:ap-southeast-2:123456789012:key/test",
        CiphertextBlob=b"ciphertext",
        EncryptionContext={
            "flowform_purpose": "startup_validation",
            "flowform_environment": "dev",
        },
    )


def test_secret_read_failure_aborts_startup_without_exposing_secret_details() -> None:
    clients = _clients()
    clients.secretsmanager.get_secret_value.side_effect = RuntimeError("sensitive provider detail")

    with pytest.raises(InitializationError) as error:
        validate_aws_runtime_access(settings=_settings(), clients=clients)

    assert "unable to read" in str(error.value)
    assert "sensitive provider detail" not in str(error.value)
    clients.kms.encrypt.assert_not_called()


def test_kms_round_trip_mismatch_aborts_startup() -> None:
    clients = _clients()
    clients.kms.decrypt.return_value = {"Plaintext": b"wrong-value"}

    with pytest.raises(InitializationError, match="unable to encrypt and decrypt"):
        validate_aws_runtime_access(settings=_settings("prod"), clients=clients)
