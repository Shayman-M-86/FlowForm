import logging

from flask import Flask
from sqlalchemy.orm import Session

from app.core.extensions import db_manager
from app.domain.permissions import PERMISSIONS
from app.repositories import permissions_repo as per

logger = logging.getLogger(__name__)


def seed_permissions(db: Session) -> None:
    """Insert any missing application permissions."""
    existing = per.list_permission_names(db)
    missing = [name for name in PERMISSIONS.all() if name not in existing]

    if missing:
        logger.info("Seeding missing permissions: %s", missing)
        per.create_permissions(db, missing)


def init_seed_data(app: Flask) -> None:
    """Seed required application data."""
    with app.app_context():
        db = db_manager.create_core_session()
        try:
            seed_permissions(db)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
