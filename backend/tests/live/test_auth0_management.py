"""Read-only credential and scope smoke test against the real Auth0 tenant."""

from __future__ import annotations

import pytest

from app.middleware.auth.auth0 import ManagementApiClient
from tests.live.helpers import require_live_env

pytestmark = pytest.mark.live_external


def test_live_auth0_management_credentials_and_scopes() -> None:
    client = ManagementApiClient(
        domain=require_live_env("FLOWFORM_LIVE_AUTH0_MGMT_DOMAIN"),
        client_id=require_live_env("FLOWFORM_LIVE_AUTH0_MGMT_ID"),
        client_secret=require_live_env("FLOWFORM_LIVE_AUTH0_MGMT_SECRET"),
    )

    client.validate_connection()
