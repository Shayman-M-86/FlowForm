"""Tests for RecognitionTokenLookupResult behavior.

Docs: Flows/shared/check-recognition-token.md
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.core import project_subject_tokens as sub_tok
from app.repositories.core.project_subjects import create_subject, set_canonical_subject
from app.schema.orm.core.project import Project
from app.schema.orm.core.project_subject import ProjectSubject
from app.services.public_submissions.core.resolution.subject_token import SubjectTokenService


def _make_subject(db: Session, *, project: Project) -> ProjectSubject:
    return create_subject(db, project_id=project.id)


def _issue_token(db: Session, *, project: Project, subject: ProjectSubject) -> str:
    _, raw = sub_tok.create_token(db, project_id=project.id, project_subject_id=subject.id)
    return raw


class TestRecognitionTokenLookupResult:
    def test_absent_token_returns_not_present(self, db_session: Session, project: Project) -> None:
        svc = SubjectTokenService()
        result = svc.lookup(db_session, project_id=project.id, raw_token="notavalidtoken")
        assert result.token_present is True
        assert result.token_valid is False
        assert result.token_id is None
        assert result.token_subject_id is None
        assert result.canonical_token_subject_id is None
        assert result.invalid_reason is not None

    def test_valid_token_returns_metadata(self, db_session: Session, project: Project) -> None:
        subject = _make_subject(db_session, project=project)
        raw = _issue_token(db_session, project=project, subject=subject)

        svc = SubjectTokenService()
        result = svc.lookup(db_session, project_id=project.id, raw_token=raw)

        assert result.token_present is True
        assert result.token_valid is True
        assert result.token_id is not None
        assert result.token_subject_id == subject.id
        assert result.canonical_token_subject_id is None  # subject is canonical
        assert result.invalid_reason is None

    def test_valid_token_does_not_update_last_used_at(
        self, db_session: Session, project: Project
    ) -> None:
        subject = _make_subject(db_session, project=project)
        raw = _issue_token(db_session, project=project, subject=subject)

        token_row = sub_tok.get_active_token_for_subject(
            db_session, project_id=project.id, project_subject_id=subject.id
        )
        assert token_row is not None
        assert token_row.last_used_at is None

        SubjectTokenService().lookup(db_session, project_id=project.id, raw_token=raw)

        db_session.refresh(token_row)
        assert token_row.last_used_at is None

    def test_tampered_token_returns_invalid(self, db_session: Session, project: Project) -> None:
        subject = _make_subject(db_session, project=project)
        _issue_token(db_session, project=project, subject=subject)

        result = SubjectTokenService().lookup(
            db_session, project_id=project.id, raw_token="tampered-garbage"
        )
        assert result.token_valid is False

    def test_revoked_token_returns_invalid(self, db_session: Session, project: Project) -> None:
        subject = _make_subject(db_session, project=project)
        raw = _issue_token(db_session, project=project, subject=subject)
        token_row = sub_tok.get_active_token_for_subject(
            db_session, project_id=project.id, project_subject_id=subject.id
        )
        assert token_row is not None
        sub_tok.revoke_token(db_session, token=token_row)

        result = SubjectTokenService().lookup(db_session, project_id=project.id, raw_token=raw)
        assert result.token_valid is False

    def test_token_wrong_project_returns_invalid(
        self, db_session: Session, project: Project
    ) -> None:
        subject = _make_subject(db_session, project=project)
        raw = _issue_token(db_session, project=project, subject=subject)

        other_project_id = project.id + 9999
        result = SubjectTokenService().lookup(
            db_session, project_id=other_project_id, raw_token=raw
        )
        assert result.token_valid is False

    def test_token_subject_with_canonical_returns_canonical_id(
        self, db_session: Session, project: Project
    ) -> None:
        canonical = _make_subject(db_session, project=project)
        alias = _make_subject(db_session, project=project)
        set_canonical_subject(db_session, subject=alias, canonical=canonical)

        raw = _issue_token(db_session, project=project, subject=alias)

        result = SubjectTokenService().lookup(db_session, project_id=project.id, raw_token=raw)
        assert result.token_valid is True
        assert result.token_subject_id == alias.id
        assert result.canonical_token_subject_id == canonical.id
