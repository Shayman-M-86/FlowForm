from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BeforeValidator,
    EmailStr,
    Field,
    StringConstraints,
)

from app.schema.api import limits
from app.schema.api.common.validators import (
    normalise_email,
    validate_future_datetime_utc,
)
from app.schema.enums import ProjectMemberStatus as ProjectMemberStatusValue

ProjectName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.PROJECT_NAME_MAX,
    ),
]

ProjectRoleName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.PROJECT_ROLE_NAME_MAX,
    ),
]

ProjectRoleDescription = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.PROJECT_ROLE_DESCRIPTION_MAX,
    ),
]

SubjectCode = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.SUBJECT_CODE_MAX,
    ),
]

PublicLinkName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.PUBLIC_LINK_NAME_MAX,
    ),
]

PublicLinkToken = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.TOKEN_MAX,
    ),
]

InviteMessage = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.INVITE_MESSAGE_MAX,
    ),
]

NormalisedEmail = Annotated[
    EmailStr,
    BeforeValidator(normalise_email),
    Field(max_length=limits.EMAIL_MAX),
]

FutureExpiresAt = Annotated[
    AwareDatetime,
    AfterValidator(validate_future_datetime_utc),
]

Slug = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.SLUG_MAX,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    ),
]

ProjectMemberStatus = Annotated[
    ProjectMemberStatusValue,
    Field(max_length=limits.PROJECT_MEMBER_STATUS_MAX),
]

SurveyTitle = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.SURVEY_TITLE_MAX,
    ),
]

SchemaIdStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.SCHEMA_ID_MAX,
    ),
]

QuestionLabel = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.QUESTION_LABEL_MAX,
    ),
]

QuestionTitle = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=0,
        max_length=limits.QUESTION_TITLE_MAX,
    ),
]

RatingLabel = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.RATING_LABEL_MAX,
    ),
]

ChoiceOptionLabel = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.CHOICE_OPTION_LABEL_MAX,
    ),
]

MatchingItemLabel = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.MATCHING_ITEM_LABEL_MAX,
    ),
]

IdToken = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.ID_TOKEN_MAX,
    ),
]

DisplayName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
    ),
]

Nickname = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
    ),
]

PictureUrl = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.URL_MAX,
    ),
]

Username = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_.\-]+$",
    ),
]

AccountEmail = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=1,
        max_length=limits.EMAIL_MAX,
    ),
]

SliderRatingNumber = Annotated[
    float,
    Field(ge=limits.RATING_RANGE_MIN, le=limits.RATING_RANGE_MAX),
]

StarsRatingNumber = Annotated[
    int,
    Field(ge=limits.RATING_STARS_MIN, le=limits.RATING_STARS_MAX),
]

EmojiRatingNumber = Annotated[
    int,
    Field(ge=limits.RATING_STARS_MIN, le=limits.RATING_STARS_MAX),
]

AnswerNumber = Annotated[
    float,
    Field(ge=limits.ANSWER_NUMBER_MIN, le=limits.ANSWER_NUMBER_MAX),
]

PhoneNumber = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.PHONE_MAX,
    ),
]
