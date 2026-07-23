"""Admin survey results service: subjects, sessions, answer slots, and deletion.

Authorization is the caller's responsibility (per doc 01 §1).

This module is the API surface only. Tree assembly lives in
``core.session_tree``, decryption in ``core.decryption``, question metadata in
``core.question_meta``, and export serialization in ``core.export``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app import tracing
from app.cache import get_app_cache
from app.crypto._internal.client_extension import get_crypto_clients
from app.crypto.locators import resolve_existing_session_locator
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import EnvelopeNotFoundError, SessionNotFoundError, SubjectNotFoundError
from app.repositories.core import project_subjects
from app.repositories.core import submission_sessions as ssr
from app.repositories.response import response_envelope_repo
from app.schema.enums import ExportFormat
from app.schema.orm.core.submission_session import SubmissionSession
from app.services.admin_results.core.export import format_export_file, to_export_rows
from app.services.admin_results.core.session_tree import SessionTreeBuilder
from app.services.results import (
    DeletionResult,
    ExportFile,
    SubjectTreeResult,
)

if TYPE_CHECKING:
    from app.cache import AppCache
    from app.crypto._internal.client_extension import CryptoClients


class AdminResultsService:
    """Admin survey results: subjects, sessions, answer slots, and deletion."""

    def __init__(
        self,
        *,
        cache: AppCache | None = None,
        clients: CryptoClients | None = None,
    ) -> None:
        self._cache = cache or get_app_cache()
        self._clients = clients or get_crypto_clients()
        self._tree = SessionTreeBuilder(cache=self._cache, clients=self._clients)

    def list_subjects(
        self,
        db: Session,
        response_db: Session,
        *,
        project_id: int,
        survey_id: int,
        page: int = 1,
        page_size: int = 20,
        include_decrypted_answer_values: bool = False,
        include_events: bool = False,
    ) -> tuple[list[SubjectTreeResult], int]:
        """List subjects with sessions in this survey, each with its session tree."""
        offset = (page - 1) * page_size
        subjects, total = project_subjects.list_subjects_by_survey(
            db,
            project_id=project_id,
            survey_id=survey_id,
            offset=offset,
            limit=page_size,
        )

        sessions_by_subject = self._tree.group_sessions_by_subject(
            db, survey_id=survey_id, subject_ids=[s.id for s in subjects]
        )

        items = [
            SubjectTreeResult(
                subject=subject,
                sessions=[
                    self._tree.build_session_result(
                        db,
                        response_db,
                        session=session,
                        include_decrypted_answer_values=include_decrypted_answer_values,
                        include_events=include_events,
                    )
                    for session in sessions_by_subject.get(subject.id, [])
                ],
            )
            for subject in subjects
        ]
        return items, total

    def get_subject_tree(
        self,
        db: Session,
        response_db: Session,
        *,
        project_id: int,
        survey_id: int,
        subject_id: UUID,
        include_decrypted_answer_values: bool = False,
        include_events: bool = False,
    ) -> SubjectTreeResult:
        """Return one subject's full session tree for this survey."""
        subject = project_subjects.get_subject_in_survey(
            db, project_id=project_id, survey_id=survey_id, subject_id=subject_id
        )
        if subject is None:
            raise SubjectNotFoundError()

        sessions = ssr.list_by_subjects(db, survey_id=survey_id, project_subject_ids=[subject_id])

        session_results = [
            self._tree.build_session_result(
                db,
                response_db,
                session=session,
                include_decrypted_answer_values=include_decrypted_answer_values,
                include_events=include_events,
            )
            for session in sessions
        ]
        return SubjectTreeResult(subject=subject, sessions=session_results)

    @tracing.action("results.export.generate")
    def export_results(
        self,
        db: Session,
        response_db: Session,
        *,
        project_id: int,
        survey_id: int,
        export_format: ExportFormat,
        session_ids: list[UUID] | None = None,
        include_decrypted_answer_values: bool = False,
    ) -> ExportFile:
        """Build a fully-formatted CSV or JSON export file for this survey's results."""
        if session_ids is not None:
            sessions = ssr.get_by_ids(db, survey_id=survey_id, session_ids=session_ids)
        else:
            sessions, _ = ssr.list_by_survey(
                db,
                project_id=project_id,
                survey_id=survey_id,
                offset=0,
                limit=10_000,
            )

        session_results = [
            self._tree.build_session_result(
                db,
                response_db,
                session=session,
                include_decrypted_answer_values=include_decrypted_answer_values,
                include_events=False,
            )
            for session in sessions
        ]
        rows = [row for result in session_results for row in to_export_rows(result)]
        export = format_export_file(rows, export_format=export_format, survey_id=survey_id)
        tracing.fields(outcome="generated", answer_count=len(rows))
        return export

    @tracing.action("results.session.delete")
    def delete_session(
        self,
        db: Session,
        response_db: Session,
        *,
        survey_id: int,
        session_id: UUID,
    ) -> DeletionResult:
        """Delete response data first, then core session.

        Response-first ordering is mandatory per doc 06.
        """
        session = _load_session(db, survey_id=survey_id, session_id=session_id)
        session_locator, _ = resolve_existing_session_locator(
            db,
            session.id,
            session.linkage_key_version,
            cache=self._cache,
            clients=self._clients,
        )

        # Step 1: Delete response DB records (cascade deletes answers)
        deleted = response_envelope_repo.delete_by_locator(response_db, session_locator)
        if not deleted:
            raise EnvelopeNotFoundError()

        commit_with_err_handle(response_db, contexts=[])
        tracing.event("flowform.results.response_deleted")

        # Step 2: Delete core session
        ssr.delete_session(db, submission_session=session)
        commit_with_err_handle(db, contexts=[session])
        tracing.event("flowform.results.core_deleted")
        tracing.fields(outcome="deleted")

        return DeletionResult(
            session_id=session.id,
            response_deleted=True,
            core_deleted=True,
        )


def _load_session(db: Session, *, survey_id: int, session_id: UUID) -> SubmissionSession:
    session = ssr.get_by_id(db, session_id)
    if session is None or session.survey_id != survey_id:
        raise SessionNotFoundError()
    return session
