from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain import public_link_rules
from app.domain.errors import LinkAuthAssignmentRequiredError, SurveyNotAccessibleError
from app.domain.guards import ensure_present
from app.repositories.core import project_participants as ppr
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User


def ensure_link_token_access(
    db: Session, *, project_id: int, link: SurveyLink, survey: Survey, actor: User | None
) -> None:
    """Check that a link token can be used to access its survey right now.

    Covers link-level state (active, not expired, not used), visibility
    compatibility between the link type and the survey, and, for authenticated
    links accessed by a logged-in actor, that the link's assigned participant
    identity is already authenticated and matches the actor. Shared by link
    preview/resolve and respondent session start so both flows enforce the same
    rules.
    """
    public_link_rules.ensure_is_active(link=link)
    public_link_rules.ensure_not_expired(link=link)
    public_link_rules.ensure_auth_satisfied(link=link, actor=actor)
    public_link_rules.ensure_not_used(link=link)
    public_link_rules.ensure_link_allowed_by_survey_visibility(survey=survey, link=link)

    if actor is None or link.link_type != "authenticated":
        return

    if link.assigned_participant_id is None:
        raise LinkAuthAssignmentRequiredError()

    participant = ensure_present(
        ppr.get_participant(db, project_id=project_id, participant_id=link.assigned_participant_id),
        error=LinkAuthAssignmentRequiredError(),
    )
    identity = participant.identity

    public_link_rules.ensure_participant_identity_authenticated(identity=identity)
    public_link_rules.ensure_actor_matches_participant_identity(identity=identity, actor=actor)


def ensure_access_grant_permitted(
    *,
    survey: Survey,
    published_version: SurveyVersion,
    link: SurveyLink | None,
) -> None:
    """Check that the resolved access method is permitted for this survey.

    Covers the cross between how the respondent arrived (public slug vs link
    type) and what the survey's visibility setting allows:

      public_slug  — only valid for visibility="public" surveys
      general link — valid for "public" and "link_only"; blocked on "private"
      private link — valid for all visibilities (participant is pre-assigned)
      authenticated link — valid for all visibilities (identity is verified)

    Call this after resolving both survey and link but before starting a
    session. The ``published_version`` parameter is accepted so callers are
    forced to have confirmed the survey is published before this check runs.
    """
    _ = published_version  # presence confirms caller has checked publishedness

    if link is None:
        # Public-slug access requires the survey to be publicly browsable.
        if survey.visibility != "public":
            raise SurveyNotAccessibleError()
        return

    if link.link_type == "general" and survey.visibility == "private":
        raise SurveyNotAccessibleError()
