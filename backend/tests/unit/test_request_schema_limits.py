from typing import Any, cast

import pytest
from pydantic import ValidationError

from app.schema.api import limits
from app.schema.api.requests.auth import BootstrapUserRequest
from app.schema.api.requests.content.questions_schemas import ChoiceOptionIn
from app.schema.api.requests.content.rule_schemas import ThenSetItemIn
from app.schema.api.requests.content.scoring_rule_schemas import MatchingPairIn
from app.schema.api.requests.projects import (
    CreateProjectRequest,
    ProjectMemberStatus,
    SendInvitationRequest,
    UpdateMemberRequest,
)
from app.schema.api.requests.public_links import (
    CreatePublicLinkRequest,
    ResolveTokenRequest,
)
from app.schema.api.requests.submissions.answers import FieldAnswerValue
from app.schema.api.requests.surveys import CreateSurveyRequest


def _too_long(limit: int) -> str:
    return "x" * (limit + 1)


@pytest.mark.parametrize(
    ("factory", "limit"),
    [
        (
            lambda value: CreateProjectRequest(name=value, slug="valid-slug"),
            limits.PROJECT_NAME_MAX,
        ),
        (
            lambda value: CreateProjectRequest(name="Valid name", slug=value),
            limits.SLUG_MAX,
        ),
        (
            lambda value: SendInvitationRequest(email=value),
            limits.EMAIL_MAX,
        ),
        (
            lambda value: UpdateMemberRequest(status=value),
            limits.PROJECT_MEMBER_STATUS_MAX,
        ),
        (
            lambda value: CreateSurveyRequest(title=value),
            limits.SURVEY_TITLE_MAX,
        ),
        (
            lambda value: CreateSurveyRequest(
                title="Valid title",
                visibility="public",
                public_slug=value,
            ),
            limits.SLUG_MAX,
        ),
        (
            lambda value: CreatePublicLinkRequest(name=value),
            limits.PUBLIC_LINK_NAME_MAX,
        ),
        (
            lambda value: CreatePublicLinkRequest(
                name="Valid link",
                assigned_email=value,
            ),
            limits.EMAIL_MAX,
        ),
        (
            lambda value: ResolveTokenRequest(token=value),
            limits.TOKEN_MAX,
        ),
        (
            lambda value: BootstrapUserRequest(id_token=value),
            limits.ID_TOKEN_MAX,
        ),
        (
            lambda value: ChoiceOptionIn(id=value, label="Choice"),
            limits.SCHEMA_ID_MAX,
        ),
        (
            lambda value: ThenSetItemIn(target_id=value, visible=True),
            limits.SCHEMA_ID_MAX,
        ),
        (
            lambda value: MatchingPairIn(left_id=value, right_id="right"),
            limits.SCHEMA_ID_MAX,
        ),
        (
            lambda value: FieldAnswerValue(value=value),
            limits.ANSWER_TEXT_MAX,
        ),
    ],
)
def test_request_string_limits_are_enforced(factory, limit: int) -> None:
    with pytest.raises(ValidationError):
        factory(_too_long(limit))


def test_send_invitation_email_is_normalized() -> None:
    request = SendInvitationRequest(email="  USER@Example.COM  ")

    assert request.email == "user@example.com"


@pytest.mark.parametrize("email", ["", "not-an-email", "missing-domain@", "@missing-local.test"])
def test_send_invitation_email_must_be_valid(email: str) -> None:
    with pytest.raises(ValidationError):
        SendInvitationRequest(email=email)


@pytest.mark.parametrize("status", ["active", "suspended"])
def test_update_member_status_allows_known_values(status: ProjectMemberStatus) -> None:
    assert UpdateMemberRequest(status=status).status == status


def test_update_member_status_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        UpdateMemberRequest(status=cast(Any, "invited"))


@pytest.mark.parametrize("factory", [UpdateMemberRequest, SendInvitationRequest])
def test_project_role_id_must_be_positive_int(factory) -> None:
    with pytest.raises(ValidationError):
        factory(role_id=0)
