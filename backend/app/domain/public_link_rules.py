from __future__ import annotations

from datetime import UTC, datetime

from app.domain.errors import LinkAssignmentMismatchError, LinkExpiredError, LinkInactiveError, LinkNotFoundError
from app.schema.orm.core.survey_access import SurveyLink


def ensure_is_not_none(*, link: SurveyLink | None) -> SurveyLink:
    if link is None:
        raise LinkNotFoundError()
    return link


def ensure_is_active(*, link: SurveyLink) -> None:
    if not link.is_active:
        raise LinkInactiveError()


def ensure_not_expired(*, link: SurveyLink) -> None:
    if link.expires_at is not None and link.expires_at < datetime.now(UTC):
        raise LinkExpiredError()


def ensure_actor_matches_assignment(*, link: SurveyLink, actor_email: str) -> None:
    if link.assigned_email is None:
        return
    if actor_email.strip().lower() != link.assigned_email.lower():
        raise LinkAssignmentMismatchError()


def ensure_survey_id_matches(*, link: SurveyLink, survey_id: int) -> None:
    if link.survey_id != survey_id:
        raise LinkNotFoundError()
