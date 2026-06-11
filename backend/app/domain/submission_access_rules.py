from __future__ import annotations

from app.domain import public_link_rules
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User


def ensure_link_token_access(*, link: SurveyLink, actor: User | None) -> None:
    actor_email = actor.email if actor is not None else None
    public_link_rules.ensure_is_active(link=link)
    public_link_rules.ensure_not_expired(link=link)
    public_link_rules.ensure_auth_satisfied(link=link, actor_email=actor_email)
    public_link_rules.ensure_actor_matches_assignment(link=link, actor_email=actor_email)
    public_link_rules.ensure_not_used(link=link)
