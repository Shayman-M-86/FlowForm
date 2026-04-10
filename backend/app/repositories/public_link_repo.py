import hashlib
import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.survey_access import SurveyPublicLink

_TOKEN_BYTES = 32


class _UnsetType:
    pass


_UNSET = _UnsetType()


def _make_token() -> tuple[str, str, str]:
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    prefix = token[:8]
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, prefix, token_hash


def list_links(db: Session, survey_id: int) -> list[SurveyPublicLink]:
    return list(db.scalars(select(SurveyPublicLink).where(SurveyPublicLink.survey_id == survey_id)))


def get_link(db: Session, survey_id: int, link_id: int) -> SurveyPublicLink | None:
    return db.scalar(
        select(SurveyPublicLink).where(
            SurveyPublicLink.survey_id == survey_id,
            SurveyPublicLink.id == link_id,
        )
    )


def create_link(
    db: Session,
    *,
    survey_id: int,
    allow_response: bool,
    expires_at: datetime | None,
) -> tuple[SurveyPublicLink, str]:
    token, prefix, token_hash = _make_token()

    link = SurveyPublicLink(
        survey_id=survey_id,
        token_prefix=prefix,
        token_hash=token_hash,
        allow_response=allow_response,
        expires_at=expires_at,
    )
    db.add(link)
    flush_with_err_handle(db, contexts=[link])
    return link, token


def update_link(
    db: Session,
    *,
    link: SurveyPublicLink,
    is_active: bool | None = None,
    allow_response: bool | None = None,
    expires_at: datetime | None | _UnsetType = _UNSET,
) -> SurveyPublicLink:
    if is_active is not None:
        link.is_active = is_active

    if allow_response is not None:
        link.allow_response = allow_response

    if not isinstance(expires_at, _UnsetType):
        link.expires_at = expires_at

    flush_with_err_handle(db, contexts=[link])
    return link


def delete_link(db: Session, link: SurveyPublicLink) -> None:
    db.delete(link)
    flush_with_err_handle(db, contexts=[link])


def resolve_token(db: Session, token: str) -> SurveyPublicLink | None:
    if len(token) < 8:
        return None

    prefix = token[:8]
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    return db.scalar(
        select(SurveyPublicLink).where(
            SurveyPublicLink.token_prefix == prefix,
            SurveyPublicLink.token_hash == token_hash,
        )
    )
