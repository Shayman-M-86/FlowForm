import pytest
from pydantic import ValidationError

from app.schema.api import limits
from app.schema.api.requests.auth import BootstrapUserRequest
from app.schema.api.requests.content.questions_schemas import ChoiceOptionIn
from app.schema.api.requests.content.rule_schemas import ThenSetItemIn
from app.schema.api.requests.content.scoring_rule_schemas import MatchingPairIn
from app.schema.api.requests.projects import CreateProjectRequest
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
