"""Session-start subject lifecycle orchestration.

This service wraps the lower-level ``SubjectResolver`` policy calculation with
the writes that must happen during session start: recognition-token lookup,
subject merges, authenticated identity writes, and token issue/rotate/mark-used
actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.logging.request_timing import request_timing
from app.repositories.core import project_subject_identities as sub_id
from app.repositories.core import project_subjects as subjects
from app.schema.orm.core.user import User
from app.services.public_submissions.core.resolution.subject_resolver import (
    SubjectResolver,
)
from app.services.public_submissions.core.resolution.subject_token import (
    SubjectTokenService,
)
from app.services.results import SubjectResolutionResult, SubmissionAccessGrant


@dataclass(frozen=True, slots=True)
class SessionSubjectResult:
    """Resolved subject context for session start."""

    final_subject_id: UUID
    subject_code: str
    raw_recognition_token: str | None


class SessionSubjectService:
    """Resolve and apply subject/token work for session start."""

    def __init__(
        self,
        *,
        subject_resolver: SubjectResolver | None = None,
        token_service: SubjectTokenService | None = None,
    ) -> None:
        self._token_service = token_service or SubjectTokenService()
        self._subject_resolver = subject_resolver or SubjectResolver(
            token_service=self._token_service,
        )

    def resolve_for_session_start(
        self,
        db: Session,
        *,
        access: SubmissionAccessGrant,
        actor: User | None,
        recognition_token: str | None,
    ) -> SessionSubjectResult:
        """Resolve final subject and apply all subject-side session-start writes."""
        resolution = self._resolve_subject(
            db,
            access=access,
            actor=actor,
            recognition_token=recognition_token,
        )
        request_timing.log("session_start.subject_resolved")

        self._apply_subject_writes(
            db,
            access=access,
            actor=actor,
            resolution=resolution,
        )

        raw_recognition_token = self._apply_token_action(
            db,
            access=access,
            resolution=resolution,
            existing_raw_token=recognition_token,
        )
        request_timing.log("session_start.token_action_applied")

        return SessionSubjectResult(
            final_subject_id=resolution.final_subject_id,
            subject_code=resolution.subject_code,
            raw_recognition_token=raw_recognition_token,
        )

    def _resolve_subject(
        self,
        db: Session,
        *,
        access: SubmissionAccessGrant,
        actor: User | None,
        recognition_token: str | None,
    ) -> SubjectResolutionResult:
        token_subject_id, canonical_token_subject_id = self._lookup_token_subject_ids(
            db,
            project_id=access.project_id,
            raw_token=recognition_token,
        )

        return self._subject_resolver.resolve(
            db,
            project_id=access.project_id,
            access_method=access.access_method,
            assigned_subject_id=access.assigned_subject_id,
            token_subject_id=token_subject_id,
            canonical_token_subject_id=canonical_token_subject_id,
            actor_user_id=actor.id if actor is not None else None,
        )

    def _lookup_token_subject_ids(
        self,
        db: Session,
        *,
        project_id: int,
        raw_token: str | None,
    ) -> tuple[UUID | None, UUID | None]:
        if not raw_token:
            return None, None

        lookup = self._token_service.lookup(
            db,
            project_id=project_id,
            raw_token=raw_token,
        )

        if not lookup.token_valid:
            return None, None

        return lookup.token_subject_id, lookup.canonical_token_subject_id

    def _apply_subject_writes(
        self,
        db: Session,
        *,
        access: SubmissionAccessGrant,
        actor: User | None,
        resolution: SubjectResolutionResult,
    ) -> None:
        self._merge_subject_if_needed(db, access=access, resolution=resolution)
        self._write_actor_identity_if_needed(
            db,
            access=access,
            actor=actor,
            resolution=resolution,
        )

    def _merge_subject_if_needed(
        self,
        db: Session,
        *,
        access: SubmissionAccessGrant,
        resolution: SubjectResolutionResult,
    ) -> None:
        if resolution.merge_subject_id is None:
            return

        if resolution.merge_into_subject_id is None:
            return

        weaker = subjects.get_subject(
            db,
            project_id=access.project_id,
            subject_id=resolution.merge_subject_id,
        )

        stronger = subjects.get_subject(
            db,
            project_id=access.project_id,
            subject_id=resolution.merge_into_subject_id,
        )

        if weaker is None or stronger is None:
            return

        subjects.set_canonical_subject(db, subject=weaker, canonical=stronger)

    def _write_actor_identity_if_needed(
        self,
        db: Session,
        *,
        access: SubmissionAccessGrant,
        actor: User | None,
        resolution: SubjectResolutionResult,
    ) -> None:
        if actor is None:
            return

        if not resolution.needs_identity_write:
            return

        sub_id.create_user_identity(
            db,
            project_id=access.project_id,
            project_subject_id=resolution.final_subject_id,
            user=actor,
        )

    def _apply_token_action(
        self,
        db: Session,
        *,
        access: SubmissionAccessGrant,
        resolution: SubjectResolutionResult,
        existing_raw_token: str | None,
    ) -> str | None:
        return self._token_service.apply_token_action(
            db,
            project_id=access.project_id,
            final_subject_id=resolution.final_subject_id,
            token_action=resolution.token_action,
            existing_raw_token=existing_raw_token,
        )
