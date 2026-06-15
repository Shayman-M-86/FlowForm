from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain import public_link_rules
from app.domain.errors import LinkAuthAssignmentRequiredError
from app.domain.guards import ensure_present
from app.repositories.core import project_participants as ppr
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User


def ensure_link_token_access(db: Session, *, project_id: int, link: SurveyLink, actor: User | None) -> None:
    """Check that a link token can be used to access its survey right now.

    Covers link-level state (active, not expired, not used) and, for
    authenticated links accessed by a logged-in actor, that the link's
    assigned participant identity is already authenticated and matches the
    actor. Shared by link preview/resolve and respondent session start so both
    flows enforce the same authenticated-link rule.
    """
    public_link_rules.ensure_is_active(link=link)
    public_link_rules.ensure_not_expired(link=link)
    public_link_rules.ensure_auth_satisfied(link=link, actor=actor)
    public_link_rules.ensure_not_used(link=link)

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
