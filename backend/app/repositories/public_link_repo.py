import hashlib
import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.survey_access import SurveyLink

_TOKEN_BYTES = 32


class _UnsetType:
    pass


_UNSET = _UnsetType()


def _make_token() -> tuple[str, str, str]:
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    prefix = token[:8]
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, prefix, token_hash


def list_links(db: Session, survey_id: int) -> list[SurveyLink]:
    return list(db.scalars(select(SurveyLink).where(SurveyLink.survey_id == survey_id)))


def get_link(db: Session, survey_id: int, link_id: int) -> SurveyLink | None:
    return db.scalar(
        select(SurveyLink).where(
            SurveyLink.survey_id == survey_id,
            SurveyLink.id == link_id,
        )
    )


def create_link(
    db: Session,
    *,
    survey_id: int,
    assigned_email: str | None,
    expires_at: datetime | None,
) -> tuple[SurveyLink, str]:
    token, prefix, token_hash = _make_token()

    link = SurveyLink(
        survey_id=survey_id,
        token_prefix=prefix,
        token_hash=token_hash,
        assigned_email=assigned_email,
        expires_at=expires_at,
    )
    db.add(link)
    flush_with_err_handle(db, contexts=[link])
    return link, token


def update_link(
    db: Session,
    *,
    link: SurveyLink,
    is_active: bool | None = None,
    assigned_email: str | None | _UnsetType = _UNSET,
    expires_at: datetime | None | _UnsetType = _UNSET,
) -> SurveyLink:
    if is_active is not None:
        link.is_active = is_active

    if not isinstance(assigned_email, _UnsetType):
        link.assigned_email = assigned_email

    if not isinstance(expires_at, _UnsetType):
        link.expires_at = expires_at

    flush_with_err_handle(db, contexts=[link])
    return link


def delete_link(db: Session, link: SurveyLink) -> None:
    db.delete(link)
    flush_with_err_handle(db, contexts=[link])


def resolve_token(db: Session, token: str) -> SurveyLink | None:
    if len(token) < 8:
        return None

    prefix = token[:8]
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    return db.scalar(
        select(SurveyLink).where(
            SurveyLink.token_prefix == prefix,
            SurveyLink.token_hash == token_hash,
        )
    )


UNSET = _UNSET
