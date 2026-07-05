from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest  # type: ignore[import]

from app.domain.errors import (
    LinkAuthAssignmentRequiredError,
    PrivateSurveyAssignedEmailRequiredError,
)
from app.services.survey_links import SurveyLinkService


def test_service_rejects_auth_required_link_without_assignment() -> None:
    survey = SimpleNamespace(visibility="link_only")

    with pytest.raises(LinkAuthAssignmentRequiredError):
        SurveyLinkService()._ensure_link_allowed_by_visibility(
            survey=cast(Any, survey),
            link_type="authenticated",
            assigned_participant_id=None,
        )


def test_service_allows_private_participant_link_without_auth() -> None:
    # A "private invite link": assigned to a participant but not requiring sign-in.
    # Bearer-token possession is the proof of identity, so this is allowed.
    survey = SimpleNamespace(visibility="link_only")

    SurveyLinkService()._ensure_link_allowed_by_visibility(
        survey=cast(Any, survey),
        link_type="private",
        assigned_participant_id=UUID("00000000-0000-0000-0000-000000000001"),
    )


def test_service_still_rejects_private_link_without_auth_assignment() -> None:
    survey = SimpleNamespace(visibility="private")

    with pytest.raises(PrivateSurveyAssignedEmailRequiredError):
        SurveyLinkService()._ensure_link_allowed_by_visibility(
            survey=cast(Any, survey),
            link_type="general",
            assigned_participant_id=None,
        )
