from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.response_store import ResponseStore

DEFAULT_PLATFORM_RESPONSE_STORE_NAME = "Platform Primary"
DEFAULT_PLATFORM_RESPONSE_STORE_TYPE = "platform_postgres"
DEFAULT_PLATFORM_RESPONSE_STORE_CONNECTION_REFERENCE = {
    "driver": "postgres",
    "schema": "public",
    "database": "flowform_response",
}


def get_platform_primary_store(db: Session, project_id: int) -> ResponseStore | None:
    return db.scalar(
        select(ResponseStore).where(
            ResponseStore.project_id == project_id,
            ResponseStore.name == DEFAULT_PLATFORM_RESPONSE_STORE_NAME,
        )
    )


def get_or_create_platform_primary_store(
    db: Session,
    project_id: int,
    *,
    created_by_user_id: int | None = None,
) -> ResponseStore:
    store = get_platform_primary_store(db, project_id)
    if store is not None:
        return store

    store = ResponseStore(
        project_id=project_id,
        name=DEFAULT_PLATFORM_RESPONSE_STORE_NAME,
        store_type=DEFAULT_PLATFORM_RESPONSE_STORE_TYPE,
        connection_reference=DEFAULT_PLATFORM_RESPONSE_STORE_CONNECTION_REFERENCE,
        is_active=True,
        created_by_user_id=created_by_user_id,
    )
    db.add(store)
    flush_with_err_handle(db)
    return store
