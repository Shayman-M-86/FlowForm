from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.survey_encryption_key import SurveyEncryptionKey


def get_by_survey(db: Session, survey_id: int) -> SurveyEncryptionKey | None:
    return db.scalar(
        select(SurveyEncryptionKey).where(SurveyEncryptionKey.survey_id == survey_id)
    )


def get_by_project_survey(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
) -> SurveyEncryptionKey | None:
    return db.scalar(
        select(SurveyEncryptionKey).where(
            SurveyEncryptionKey.project_id == project_id,
            SurveyEncryptionKey.survey_id == survey_id,
        )
    )


def create(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
    wrapped_survey_branch_key: bytes,
    kms_key_arn: str,
    kms_context_version: int,
) -> SurveyEncryptionKey:
    key = SurveyEncryptionKey(
        project_id=project_id,
        survey_id=survey_id,
        wrapped_survey_branch_key=wrapped_survey_branch_key,
        kms_key_arn=kms_key_arn,
        kms_context_version=kms_context_version,
    )
    db.add(key)
    flush_with_err_handle(db, contexts=[key])
    return key


def delete(db: Session, *, key: SurveyEncryptionKey) -> None:
    db.delete(key)
    flush_with_err_handle(db, contexts=[key])
