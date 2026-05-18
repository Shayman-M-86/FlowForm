from types import SimpleNamespace
from typing import Any, cast

import pytest  # type: ignore[import]

from app.domain.errors import LinkAuthAssignmentRequiredError, PrivateSurveyAssignedEmailRequiredError
from app.services.public_links import SurveyLinkService


def test_service_rejects_auth_required_link_without_assignment() -> None:
    survey = SimpleNamespace(visibility="link_only")

    with pytest.raises(LinkAuthAssignmentRequiredError):
        SurveyLinkService()._ensure_link_allowed_by_visibility(  
            survey=cast(Any, survey),
            requires_auth=True,
            assigned_email=None,
        )


def test_service_still_rejects_private_link_without_auth_assignment() -> None:
    survey = SimpleNamespace(visibility="private")

    with pytest.raises(PrivateSurveyAssignedEmailRequiredError):
        SurveyLinkService()._ensure_link_allowed_by_visibility(  
            survey=cast(Any, survey),
            requires_auth=False,
            assigned_email=None,
        )
