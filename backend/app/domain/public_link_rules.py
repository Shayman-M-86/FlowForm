from __future__ import annotations

from datetime import UTC, datetime

from app.domain.errors import (
    LinkAlreadyUsedError,
    LinkAssignmentMismatchError,
    LinkAuthRequiredError,
    LinkExpiredError,
    LinkInactiveError,
    LinkNotFoundError,
    LinkParticipantVerificationRequiredError,
)
from app.schema.orm.core.project_subject import ProjectSubjectIdentity
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User


def ensure_is_active(*, link: SurveyLink) -> None:
    if not link.is_active:
        raise LinkInactiveError()


def ensure_not_expired(*, link: SurveyLink) -> None:
    if link.expires_at is not None and link.expires_at < datetime.now(UTC):
        raise LinkExpiredError()


def ensure_not_used(*, link: SurveyLink) -> None:
    """Single-use links, derived from participant assignment, cannot be used twice."""
    if link.is_single_use and link.used_at is not None:
        raise LinkAlreadyUsedError()


def ensure_auth_satisfied(*, link: SurveyLink, actor: User | None) -> None:
    """A link that requires auth must be accessed by an authenticated user."""
    if link.link_type == "authenticated" and actor is None:
        raise LinkAuthRequiredError()


def ensure_participant_identity_authenticated(*, identity: ProjectSubjectIdentity) -> None:
    """Authenticated links require a participant identity already linked to a user."""
    if identity.identity_type != "authenticated_user" or identity.user_id is None:
        raise LinkParticipantVerificationRequiredError()


def ensure_actor_matches_participant_identity(*, identity: ProjectSubjectIdentity, actor: User) -> None:
    if identity.user_id != actor.id:
        raise LinkAssignmentMismatchError()


def ensure_survey_id_matches(*, link: SurveyLink, survey_id: int) -> None:
    if link.survey_id != survey_id:
        raise LinkNotFoundError()
