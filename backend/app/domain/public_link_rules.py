from __future__ import annotations

from datetime import UTC, datetime

from app.domain.errors import LinkExpiredError, LinkInactiveError, LinkNoResponseError, LinkNotFoundError
from app.schema.orm.core.survey_access import SurveyPublicLink


def ensure_is_not_none(*, link: SurveyPublicLink | None) -> SurveyPublicLink:
    if link is None:
        raise LinkNotFoundError()
    return link


def ensure_is_active(*, link: SurveyPublicLink) -> None:
    if not link.is_active:
        raise LinkInactiveError()


def ensure_not_expired(*, link: SurveyPublicLink) -> None:
    if link.expires_at is not None and link.expires_at < datetime.now(UTC):
        raise LinkExpiredError()


def ensure_allows_response(*, link: SurveyPublicLink) -> None:
    if not link.allow_response:
        raise LinkNoResponseError()

def ensure_survey_id_matches(*, link: SurveyPublicLink, survey_id: int) -> None:
    if link.survey_id != survey_id:
        raise LinkNotFoundError()
