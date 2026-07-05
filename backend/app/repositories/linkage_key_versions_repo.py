import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.linkage_key_version import LinkageKeyVersion


def get_aws_version_id(db: Session, version: int) -> uuid.UUID | None:
    """Return the AWS secret version ID for a given app-level linkage key version."""
    return db.scalar(
        select(LinkageKeyVersion.aws_secret_version_id).where(
            LinkageKeyVersion.version == version
        )
    )


def version_exists(db: Session, version: int) -> bool:
    """Check whether an app-level linkage key version row exists."""
    return (
        db.scalar(
            select(LinkageKeyVersion.version).where(
                LinkageKeyVersion.version == version
            )
        )
        is not None
    )


def insert_version(
    db: Session,
    *,
    version: int,
    aws_secret_id: str,
    aws_secret_version_id: uuid.UUID,
    is_current: bool,
) -> None:
    """Insert a new linkage key version row and flush."""
    if is_current:
        db.execute(
            update(LinkageKeyVersion)
            .where(LinkageKeyVersion.is_current.is_(True))
            .values(is_current=False)
        )
    row = LinkageKeyVersion(
        version=version,
        aws_secret_id=aws_secret_id,
        aws_secret_version_id=aws_secret_version_id,
        is_current=is_current,
    )
    db.add(row)
    flush_with_err_handle(db)
