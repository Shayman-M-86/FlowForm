"""Focused tests for SubjectResolutionResult — canonical resolution and token action.

Covers the doc-driven decision tables from:
  shared/subject-resolution.md — open-access and assigned-access tables
  shared/logged-in-reconciliation.md — conflict rule
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.repositories.core import project_subject_identities as sub_id
from app.repositories.core import project_subject_tokens as sub_tok
from app.repositories.core import project_subjects as sub_repo
from app.schema.orm.core.project import Project
from app.schema.orm.core.project_subject import ProjectSubject, ProjectSubjectToken
from app.schema.orm.core.user import User
from app.services.public_submissions.core.resolution.subject_resolver import SubjectResolver

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_subject(
    db: Session, *, project_id: int, subject_code: str = "sub-test"
) -> ProjectSubject:
    return sub_repo.create_subject(db, project_id=project_id, subject_code=subject_code)


def _make_token(
    db: Session, *, project_id: int, subject: ProjectSubject, raw: str = "tok-abc"
) -> ProjectSubjectToken:
    token = ProjectSubjectToken(
        project_id=project_id,
        project_subject_id=subject.id,
        token_hash=sub_tok.hash_recognition_token(raw),
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(token)
    db.flush()
    return token


def _resolver() -> SubjectResolver:
    return SubjectResolver()


# ---------------------------------------------------------------------------
# Open-access: no actor, no token
# ---------------------------------------------------------------------------


def test_open_access_no_token_no_actor_creates_subject_issues_token(
    db_session: Session, project: Project
) -> None:
    result = _resolver().resolve(
        db_session,
        project_id=project.id,
        access_method="public_slug",
        assigned_subject_id=None,
        token_subject_id=None,
        canonical_token_subject_id=None,
        actor_user_id=None,
    )

    assert result.subject_source == "anonymous_created"
    assert result.token_action == "issue"
    assert result.merge_subject_id is None


# ---------------------------------------------------------------------------
# Open-access: no actor, valid token
# ---------------------------------------------------------------------------


def test_open_access_valid_token_no_actor_mark_used(
    db_session: Session, project: Project
) -> None:
    subject = _make_subject(db_session, project_id=project.id, subject_code="sub-tok")

    result = _resolver().resolve(
        db_session,
        project_id=project.id,
        access_method="public_slug",
        assigned_subject_id=None,
        token_subject_id=subject.id,
        canonical_token_subject_id=None,
        actor_user_id=None,
    )

    assert result.final_subject_id == subject.id
    assert result.subject_source == "recognition_token"
    assert result.token_action == "mark_used"
    assert result.merge_subject_id is None


def test_open_access_token_pointing_to_non_canonical_resolves_to_canonical(
    db_session: Session, project: Project
) -> None:
    canonical = _make_subject(db_session, project_id=project.id, subject_code="canonical")
    weaker = _make_subject(db_session, project_id=project.id, subject_code="weaker")
    sub_repo.set_canonical_subject(db_session, subject=weaker, canonical=canonical)

    result = _resolver().resolve(
        db_session,
        project_id=project.id,
        access_method="public_slug",
        assigned_subject_id=None,
        token_subject_id=weaker.id,
        canonical_token_subject_id=canonical.id,
        actor_user_id=None,
    )

    # Uses the canonical subject, not the weaker one.
    assert result.final_subject_id == canonical.id
    assert result.subject_source == "recognition_token"
    assert result.token_action == "mark_used"


# ---------------------------------------------------------------------------
# Open-access: logged-in user, no identity, no token
# ---------------------------------------------------------------------------


def test_open_access_logged_in_no_identity_no_token_creates_subject(
    db_session: Session, project: Project, user: User
) -> None:
    result = _resolver().resolve(
        db_session,
        project_id=project.id,
        access_method="public_slug",
        assigned_subject_id=None,
        token_subject_id=None,
        canonical_token_subject_id=None,
        actor_user_id=user.id,
    )

    assert result.subject_source == "authenticated_user"
    assert result.token_action == "issue"
    assert result.needs_identity_write is True
    assert result.merge_subject_id is None


# ---------------------------------------------------------------------------
# Open-access: logged-in user, no identity, valid token
# ---------------------------------------------------------------------------


def test_open_access_logged_in_no_identity_valid_token_attaches(
    db_session: Session, project: Project, user: User
) -> None:
    subject = _make_subject(db_session, project_id=project.id, subject_code="tok-subject")

    result = _resolver().resolve(
        db_session,
        project_id=project.id,
        access_method="public_slug",
        assigned_subject_id=None,
        token_subject_id=subject.id,
        canonical_token_subject_id=None,
        actor_user_id=user.id,
    )

    assert result.final_subject_id == subject.id
    assert result.subject_source == "authenticated_user"
    assert result.token_action == "mark_used"
    assert result.needs_identity_write is True
    assert result.merge_subject_id is None


# ---------------------------------------------------------------------------
# Open-access: logged-in user, identity exists, no token
# ---------------------------------------------------------------------------


def test_open_access_logged_in_identity_exists_no_token_issues(
    db_session: Session, project: Project, user: User
) -> None:
    subject = _make_subject(db_session, project_id=project.id, subject_code="identity-subject")
    sub_id.create_user_identity(
        db_session, project_id=project.id, project_subject_id=subject.id, user=user
    )

    result = _resolver().resolve(
        db_session,
        project_id=project.id,
        access_method="public_slug",
        assigned_subject_id=None,
        token_subject_id=None,
        canonical_token_subject_id=None,
        actor_user_id=user.id,
    )

    assert result.final_subject_id == subject.id
    assert result.subject_source == "authenticated_user"
    assert result.token_action == "issue"
    assert result.needs_identity_write is False


# ---------------------------------------------------------------------------
# Open-access: logged-in user, identity exists, token same canonical
# ---------------------------------------------------------------------------


def test_open_access_logged_in_identity_token_same_canonical_mark_used(
    db_session: Session, project: Project, user: User
) -> None:
    subject = _make_subject(db_session, project_id=project.id, subject_code="shared-canonical")
    sub_id.create_user_identity(
        db_session, project_id=project.id, project_subject_id=subject.id, user=user
    )

    result = _resolver().resolve(
        db_session,
        project_id=project.id,
        access_method="public_slug",
        assigned_subject_id=None,
        token_subject_id=subject.id,
        canonical_token_subject_id=None,
        actor_user_id=user.id,
    )

    assert result.final_subject_id == subject.id
    assert result.subject_source == "authenticated_user"
    assert result.token_action == "mark_used"
    assert result.needs_identity_write is False
    assert result.merge_subject_id is None


# ---------------------------------------------------------------------------
# Open-access: logged-in user, identity exists, token different canonical — merge
# ---------------------------------------------------------------------------


def test_open_access_logged_in_identity_token_different_canonical_merges(
    db_session: Session, project: Project, user: User
) -> None:
    identity_subject = _make_subject(db_session, project_id=project.id, subject_code="identity")
    token_subject = _make_subject(db_session, project_id=project.id, subject_code="token")
    sub_id.create_user_identity(
        db_session, project_id=project.id, project_subject_id=identity_subject.id, user=user
    )

    result = _resolver().resolve(
        db_session,
        project_id=project.id,
        access_method="public_slug",
        assigned_subject_id=None,
        token_subject_id=token_subject.id,
        canonical_token_subject_id=None,
        actor_user_id=user.id,
    )

    assert result.final_subject_id == identity_subject.id
    assert result.subject_source == "authenticated_user"
    assert result.token_action == "rotate"
    assert result.needs_identity_write is False
    assert result.merge_subject_id == token_subject.id
    assert result.merge_into_subject_id == identity_subject.id


# ---------------------------------------------------------------------------
# Assigned-access: no token — issue
# ---------------------------------------------------------------------------


def test_assigned_no_token_issues_recognition_token(
    db_session: Session, project: Project
) -> None:
    assigned = _make_subject(db_session, project_id=project.id, subject_code="assigned")

    result = _resolver().resolve(
        db_session,
        project_id=project.id,
        access_method="private_link",
        assigned_subject_id=assigned.id,
        token_subject_id=None,
        canonical_token_subject_id=None,
        actor_user_id=None,
    )

    assert result.final_subject_id == assigned.id
    assert result.subject_source == "assigned_link"
    assert result.token_action == "issue"
    assert result.merge_subject_id is None


# ---------------------------------------------------------------------------
# Assigned-access: token same canonical as assigned — keep
# ---------------------------------------------------------------------------


def test_assigned_token_same_canonical_keep(
    db_session: Session, project: Project
) -> None:
    assigned = _make_subject(db_session, project_id=project.id, subject_code="assigned-same")

    result = _resolver().resolve(
        db_session,
        project_id=project.id,
        access_method="private_link",
        assigned_subject_id=assigned.id,
        token_subject_id=assigned.id,
        canonical_token_subject_id=None,
        actor_user_id=None,
    )

    assert result.final_subject_id == assigned.id
    assert result.subject_source == "assigned_link"
    assert result.token_action == "keep"
    assert result.merge_subject_id is None


# ---------------------------------------------------------------------------
# Assigned-access: token different canonical — merge and rotate
# ---------------------------------------------------------------------------


def test_assigned_token_different_canonical_merges_and_rotates(
    db_session: Session, project: Project
) -> None:
    assigned = _make_subject(db_session, project_id=project.id, subject_code="assigned-strong")
    stray = _make_subject(db_session, project_id=project.id, subject_code="stray-token")

    result = _resolver().resolve(
        db_session,
        project_id=project.id,
        access_method="private_link",
        assigned_subject_id=assigned.id,
        token_subject_id=stray.id,
        canonical_token_subject_id=None,
        actor_user_id=None,
    )

    assert result.final_subject_id == assigned.id
    assert result.subject_source == "assigned_link"
    assert result.token_action == "rotate"
    assert result.merge_subject_id == stray.id
    assert result.merge_into_subject_id == assigned.id


# ---------------------------------------------------------------------------
# Assigned-access: assigned subject itself is non-canonical — resolves to canonical
# ---------------------------------------------------------------------------


def test_assigned_subject_non_canonical_resolves_to_canonical(
    db_session: Session, project: Project
) -> None:
    canonical = _make_subject(db_session, project_id=project.id, subject_code="real-canonical")
    alias = _make_subject(db_session, project_id=project.id, subject_code="alias")
    sub_repo.set_canonical_subject(db_session, subject=alias, canonical=canonical)

    result = _resolver().resolve(
        db_session,
        project_id=project.id,
        access_method="private_link",
        assigned_subject_id=alias.id,
        token_subject_id=None,
        canonical_token_subject_id=None,
        actor_user_id=None,
    )

    # Resolver follows canonical_subject_id.
    assert result.final_subject_id == canonical.id
    assert result.subject_source == "assigned_link"
    assert result.token_action == "issue"
