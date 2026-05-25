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
    CreateProjectRoleRequest,
    ProjectMemberStatus,
    SendInvitationRequest,
    UpdateMemberRequest,
)
from app.schema.api.requests.public_links import (
    CreatePublicLinkRequest,
    ResolveTokenRequest,
)
from app.schema.api.requests.submissions.answers import (
    ChoiceAnswerIn,
    ChoiceAnswerValue,
    FieldAnswerValue,
    MatchingAnswerValue,
    MatchPair,
)
from app.schema.api.requests.submissions.create import LinkSubmissionRequest, SlugSubmissionRequest
from app.schema.api.requests.surveys import CreateSurveyRequest, UpdateSurveyRequest


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
            lambda value: CreateProjectRoleRequest(name=value),
            limits.PROJECT_ROLE_NAME_MAX,
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


@pytest.mark.parametrize("factory", [CreateSurveyRequest, UpdateSurveyRequest])
def test_default_response_store_id_must_be_positive_int(factory) -> None:
    with pytest.raises(ValidationError):
        factory(default_response_store_id=0)


def test_choice_answer_selected_list_limit_is_enforced() -> None:
    selected = [f"option-{index}" for index in range(limits.ANSWER_LIST_ITEMS_MAX + 1)]

    with pytest.raises(ValidationError):
        ChoiceAnswerValue(selected=selected)


def test_matching_answer_matches_list_limit_is_enforced() -> None:
    matches = [
        MatchPair(left_id=f"left-{index}", right_id=f"right-{index}")
        for index in range(limits.ANSWER_LIST_ITEMS_MAX + 1)
    ]

    with pytest.raises(ValidationError):
        MatchingAnswerValue(matches=matches)


@pytest.mark.parametrize(
    ("factory", "payload"),
    [
        (LinkSubmissionRequest, {"token": "token"}),
        (SlugSubmissionRequest, {"public_slug": "public-slug"}),
    ],
)
def test_submission_survey_version_id_must_be_positive_int(factory, payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        factory(survey_version_id=0, answers=[_choice_answer()], **payload)


def test_submission_answers_list_limit_is_enforced() -> None:
    answers: list[Any] = [_choice_answer(index) for index in range(limits.ANSWER_LIST_ITEMS_MAX + 1)]

    with pytest.raises(ValidationError):
        LinkSubmissionRequest(token="token", survey_version_id=1, answers=answers)


def test_submission_metadata_item_limit_is_enforced() -> None:
    metadata = {f"key-{index}": index for index in range(limits.SUBMISSION_METADATA_ITEMS_MAX + 1)}

    with pytest.raises(ValidationError):
        LinkSubmissionRequest(token="token", survey_version_id=1, answers=[_choice_answer()], metadata=metadata)


def _choice_answer(index: int = 1) -> ChoiceAnswerIn:
    return ChoiceAnswerIn(
        question_key=f"question-{index}",
        answer_family="choice",
        answer_value=ChoiceAnswerValue(selected=[f"option-{index}"]),
    )
