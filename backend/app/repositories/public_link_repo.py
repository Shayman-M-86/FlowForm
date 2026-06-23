import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.enums import SurveyLinkAssignmentSource, SurveyLinkType
from app.schema.orm.core.survey_access import SurveyLink

_TOKEN_BYTES = 32


class _UnsetType:
    pass


_UNSET = _UnsetType()


def _make_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


def list_links(db: Session, survey_id: int) -> list[SurveyLink]:
    return list(db.scalars(select(SurveyLink).where(SurveyLink.survey_id == survey_id)))


def get_link(db: Session, survey_id: int, link_id: uuid.UUID) -> SurveyLink | None:
    return db.scalar(
        select(SurveyLink).where(
            SurveyLink.survey_id == survey_id,
            SurveyLink.id == link_id,
        )
    )


def create_link(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
    name: str,
    link_type: SurveyLinkType,
    assignment_source: SurveyLinkAssignmentSource,
    assigned_participant_id: uuid.UUID | None,
    expires_at: datetime | None,
) -> SurveyLink:
    token = _make_token()

    link = SurveyLink(
        project_id=project_id,
        survey_id=survey_id,
        name=name,
        token=token,
        link_type=link_type,
        assignment_source=assignment_source,
        assigned_participant_id=assigned_participant_id,
        expires_at=expires_at,
    )
    db.add(link)
    flush_with_err_handle(db, contexts=[link])
    return link


def update_link(
    db: Session,
    *,
    link: SurveyLink,
    is_active: bool | None = None,
    name: str | None = None,
    link_type: SurveyLinkType | _UnsetType = _UNSET,
    assignment_source: SurveyLinkAssignmentSource | _UnsetType = _UNSET,
    assigned_participant_id: uuid.UUID | None | _UnsetType = _UNSET,
    expires_at: datetime | None | _UnsetType = _UNSET,
) -> SurveyLink:
    if is_active is not None:
        link.is_active = is_active

    if name is not None:
        link.name = name

    if not isinstance(link_type, _UnsetType):
        link.link_type = link_type

    if not isinstance(assignment_source, _UnsetType):
        link.assignment_source = assignment_source

    if not isinstance(assigned_participant_id, _UnsetType):
        link.assigned_participant_id = assigned_participant_id

    if not isinstance(expires_at, _UnsetType):
        link.expires_at = expires_at

    flush_with_err_handle(db, contexts=[link])
    return link


def mark_used(db: Session, *, link: SurveyLink) -> SurveyLink:
    """Mark a single-use link as used. No-op if already used."""
    if link.used_at is None:
        link.used_at = datetime.now(UTC)
    flush_with_err_handle(db, contexts=[link])
    return link


def delete_link(db: Session, link: SurveyLink) -> None:
    db.delete(link)
    flush_with_err_handle(db, contexts=[link])


def resolve_token(db: Session, token: str) -> SurveyLink | None:
    if not token:
        return None

    return db.scalar(
        select(SurveyLink).where(SurveyLink.token == token)
    )


UNSET = _UNSET
