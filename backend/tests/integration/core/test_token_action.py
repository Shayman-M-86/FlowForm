"""Tests for SubjectTokenService.apply_token_action().

Docs: Flows/shared/issue-or-rotate-recognition-token.md
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.core import project_subject_tokens as sub_tok
from app.repositories.core.project_subjects import create_subject
from app.schema.orm.core.project import Project
from app.schema.orm.core.project_subject import ProjectSubject
from app.services.public_submissions.core.resolution.subject_token import SubjectTokenService


def _make_subject(db: Session, *, project: Project) -> ProjectSubject:
    return create_subject(db, project_id=project.id)


def _issue_token(db: Session, *, project: Project, subject: ProjectSubject) -> str:
    _, raw = sub_tok.create_token(db, project_id=project.id, project_subject_id=subject.id)
    return raw


class TestApplyTokenActionIssue:
    def test_issue_creates_token_and_returns_raw(self, db_session: Session, project: Project) -> None:
        subject = _make_subject(db_session, project=project)
        svc = SubjectTokenService()

        raw = svc.apply_token_action(
            db_session,
            project_id=project.id,
            final_subject_id=subject.id,
            token_action="issue",
        )

        assert raw is not None
        token_row = sub_tok.get_active_token_for_subject(
            db_session, project_id=project.id, project_subject_id=subject.id
        )
        assert token_row is not None
        assert sub_tok.get_active_token(db_session, project_id=project.id, raw_token=raw) is not None

    def test_issue_returns_new_raw_token_even_when_existing(
        self, db_session: Session, project: Project
    ) -> None:
        subject = _make_subject(db_session, project=project)
        old_raw = _issue_token(db_session, project=project, subject=subject)
        svc = SubjectTokenService()

        new_raw = svc.apply_token_action(
            db_session,
            project_id=project.id,
            final_subject_id=subject.id,
            token_action="issue",
        )

        assert new_raw is not None
        assert new_raw != old_raw


class TestApplyTokenActionRotate:
    def test_rotate_revokes_old_token_and_returns_new(
        self, db_session: Session, project: Project
    ) -> None:
        subject = _make_subject(db_session, project=project)
        old_raw = _issue_token(db_session, project=project, subject=subject)
        svc = SubjectTokenService()

        new_raw = svc.apply_token_action(
            db_session,
            project_id=project.id,
            final_subject_id=subject.id,
            token_action="rotate",
        )

        assert new_raw is not None
        assert new_raw != old_raw
        # old token is now invalid
        assert sub_tok.get_active_token(db_session, project_id=project.id, raw_token=old_raw) is None
        # new token is valid
        assert sub_tok.get_active_token(db_session, project_id=project.id, raw_token=new_raw) is not None

    def test_rotate_with_no_existing_token_still_issues(
        self, db_session: Session, project: Project
    ) -> None:
        subject = _make_subject(db_session, project=project)
        svc = SubjectTokenService()

        new_raw = svc.apply_token_action(
            db_session,
            project_id=project.id,
            final_subject_id=subject.id,
            token_action="rotate",
        )

        assert new_raw is not None
        assert sub_tok.get_active_token(db_session, project_id=project.id, raw_token=new_raw) is not None


class TestApplyTokenActionMarkUsed:
    def test_mark_used_updates_last_used_at_and_returns_existing_raw(
        self, db_session: Session, project: Project
    ) -> None:
        subject = _make_subject(db_session, project=project)
        raw = _issue_token(db_session, project=project, subject=subject)
        token_row = sub_tok.get_active_token_for_subject(
            db_session, project_id=project.id, project_subject_id=subject.id
        )
        assert token_row is not None
        assert token_row.last_used_at is None

        svc = SubjectTokenService()
        returned_raw = svc.apply_token_action(
            db_session,
            project_id=project.id,
            final_subject_id=subject.id,
            token_action="mark_used",
            existing_raw_token=raw,
        )

        db_session.refresh(token_row)
        assert token_row.last_used_at is not None
        assert returned_raw == raw

    def test_mark_used_no_existing_token_returns_raw_arg(
        self, db_session: Session, project: Project
    ) -> None:
        subject = _make_subject(db_session, project=project)
        svc = SubjectTokenService()

        returned = svc.apply_token_action(
            db_session,
            project_id=project.id,
            final_subject_id=subject.id,
            token_action="mark_used",
            existing_raw_token="some-raw-token",
        )

        assert returned == "some-raw-token"


class TestApplyTokenActionKeepAndNone:
    def test_keep_returns_none(self, db_session: Session, project: Project) -> None:
        subject = _make_subject(db_session, project=project)
        _issue_token(db_session, project=project, subject=subject)
        svc = SubjectTokenService()

        result = svc.apply_token_action(
            db_session,
            project_id=project.id,
            final_subject_id=subject.id,
            token_action="keep",
            existing_raw_token="existing",
        )

        assert result is None

    def test_none_action_returns_none(self, db_session: Session, project: Project) -> None:
        subject = _make_subject(db_session, project=project)
        svc = SubjectTokenService()

        result = svc.apply_token_action(
            db_session,
            project_id=project.id,
            final_subject_id=subject.id,
            token_action="none",
        )

        assert result is None

    def test_keep_does_not_modify_existing_token(
        self, db_session: Session, project: Project
    ) -> None:
        subject = _make_subject(db_session, project=project)
        raw = _issue_token(db_session, project=project, subject=subject)
        token_row = sub_tok.get_active_token_for_subject(
            db_session, project_id=project.id, project_subject_id=subject.id
        )
        assert token_row is not None

        SubjectTokenService().apply_token_action(
            db_session,
            project_id=project.id,
            final_subject_id=subject.id,
            token_action="keep",
            existing_raw_token=raw,
        )

        db_session.refresh(token_row)
        assert token_row.revoked_at is None
        assert token_row.last_used_at is None
