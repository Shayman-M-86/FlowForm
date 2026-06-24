from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.repositories.core import project_subjects as psr
from app.schema.orm.core.project import Project
from app.schema.orm.core.project_subject import ProjectSubject, ProjectSubjectIdentity
from app.services.subjects import SubjectService
from tests.integration.core.factories import make_participant_chain

subject_service = SubjectService()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bare_subject(
    db: Session,
    *,
    project_id: int,
    subject_code: str = "sub-bare",
    canonical_subject_id: UUID | None = None,
) -> ProjectSubject:
    subject = ProjectSubject(
        project_id=project_id,
        subject_code=subject_code,
        canonical_subject_id=canonical_subject_id,
    )
    db.add(subject)
    db.flush()
    return subject


def _make_identity(
    db: Session,
    *,
    project_id: int,
    subject_id: UUID,
    email: str = "test@example.com",
    revoked: bool = False,
) -> ProjectSubjectIdentity:
    identity = ProjectSubjectIdentity(
        project_id=project_id,
        project_subject_id=subject_id,
        identity_type="email",
        normalized_email=email,
        revoked_at=datetime.now(UTC) if revoked else None,
    )
    db.add(identity)
    db.flush()
    return identity


# ===========================================================================
# Repository tests: list_subjects
# ===========================================================================


class TestListSubjectsRepository:
    def test_empty_project_returns_zero(
        self, db_session: Session, project: Project
    ) -> None:
        rows, total = psr.list_subjects(db_session, project_id=project.id)
        assert total == 0
        assert rows == []

    def test_returns_canonical_subjects_by_default(
        self, db_session: Session, project: Project
    ) -> None:
        canonical = _make_bare_subject(db_session, project_id=project.id, subject_code="c1")
        alias = _make_bare_subject(
            db_session,
            project_id=project.id,
            subject_code="a1",
            canonical_subject_id=canonical.id,
        )

        rows, total = psr.list_subjects(db_session, project_id=project.id)
        assert total == 1
        subject_ids = [r[0].id for r in rows]
        assert canonical.id in subject_ids
        assert alias.id not in subject_ids

    def test_canonical_status_alias(
        self, db_session: Session, project: Project
    ) -> None:
        canonical = _make_bare_subject(db_session, project_id=project.id, subject_code="c1")
        alias = _make_bare_subject(
            db_session,
            project_id=project.id,
            subject_code="a1",
            canonical_subject_id=canonical.id,
        )

        rows, total = psr.list_subjects(
            db_session, project_id=project.id, canonical_status="alias"
        )
        assert total == 1
        assert rows[0][0].id == alias.id

    def test_canonical_status_all(
        self, db_session: Session, project: Project
    ) -> None:
        canonical = _make_bare_subject(db_session, project_id=project.id, subject_code="c1")
        _make_bare_subject(
            db_session,
            project_id=project.id,
            subject_code="a1",
            canonical_subject_id=canonical.id,
        )

        rows, total = psr.list_subjects(
            db_session, project_id=project.id, canonical_status="all"
        )
        assert total == 2

    def test_is_participant_filter_true(
        self, db_session: Session, project: Project
    ) -> None:
        _make_bare_subject(db_session, project_id=project.id, subject_code="bare")
        make_participant_chain(db_session, project_id=project.id, subject_code="enrolled")

        rows, total = psr.list_subjects(
            db_session, project_id=project.id, is_participant=True
        )
        assert total == 1
        assert rows[0][0].subject_code == "enrolled"

    def test_is_participant_filter_false(
        self, db_session: Session, project: Project
    ) -> None:
        _make_bare_subject(db_session, project_id=project.id, subject_code="bare")
        make_participant_chain(db_session, project_id=project.id, subject_code="enrolled")

        rows, total = psr.list_subjects(
            db_session, project_id=project.id, is_participant=False
        )
        assert total == 1
        assert rows[0][0].subject_code == "bare"

    def test_search_by_subject_code(
        self, db_session: Session, project: Project
    ) -> None:
        _make_bare_subject(db_session, project_id=project.id, subject_code="alpha-one")
        _make_bare_subject(db_session, project_id=project.id, subject_code="beta-two")

        rows, total = psr.list_subjects(
            db_session, project_id=project.id, search="alpha"
        )
        assert total == 1
        assert rows[0][0].subject_code == "alpha-one"

    def test_search_by_identity_email(
        self, db_session: Session, project: Project
    ) -> None:
        s1 = _make_bare_subject(db_session, project_id=project.id, subject_code="s1")
        _make_identity(db_session, project_id=project.id, subject_id=s1.id, email="findme@example.com")
        _make_bare_subject(db_session, project_id=project.id, subject_code="s2")

        rows, total = psr.list_subjects(
            db_session, project_id=project.id, search="findme"
        )
        assert total == 1
        assert rows[0][0].subject_code == "s1"

    def test_search_ignores_revoked_identities(
        self, db_session: Session, project: Project
    ) -> None:
        s1 = _make_bare_subject(db_session, project_id=project.id, subject_code="s1")
        _make_identity(
            db_session, project_id=project.id, subject_id=s1.id,
            email="revoked@example.com", revoked=True,
        )

        rows, total = psr.list_subjects(
            db_session, project_id=project.id, search="revoked"
        )
        assert total == 0

    def test_active_identity_count_excludes_revoked(
        self, db_session: Session, project: Project
    ) -> None:
        s1 = _make_bare_subject(db_session, project_id=project.id, subject_code="s1")
        _make_identity(db_session, project_id=project.id, subject_id=s1.id, email="a@x.com")
        _make_identity(db_session, project_id=project.id, subject_id=s1.id, email="b@x.com")
        _make_identity(
            db_session, project_id=project.id, subject_id=s1.id,
            email="c@x.com", revoked=True,
        )

        rows, total = psr.list_subjects(db_session, project_id=project.id)
        assert total == 1
        assert rows[0][1] == 2  # active_identity_count

    def test_participant_id_populated(
        self, db_session: Session, project: Project
    ) -> None:
        participant = make_participant_chain(
            db_session, project_id=project.id, subject_code="enrolled"
        )

        rows, total = psr.list_subjects(db_session, project_id=project.id)
        assert total == 1
        assert rows[0][2] == participant.id  # participant_id

    def test_participant_id_none_for_bare_subject(
        self, db_session: Session, project: Project
    ) -> None:
        _make_bare_subject(db_session, project_id=project.id, subject_code="bare")

        rows, total = psr.list_subjects(db_session, project_id=project.id)
        assert total == 1
        assert rows[0][2] is None  # participant_id

    def test_pagination_offset_limit(
        self, db_session: Session, project: Project
    ) -> None:
        for i in range(5):
            _make_bare_subject(db_session, project_id=project.id, subject_code=f"s-{i}")

        rows, total = psr.list_subjects(
            db_session, project_id=project.id, offset=2, limit=2
        )
        assert total == 5
        assert len(rows) == 2

    def test_does_not_leak_across_projects(
        self, db_session: Session, project: Project
    ) -> None:
        from tests.integration.core.factories import make_project, make_user

        other_user = make_user(auth0_user_id="auth0|other", email="other@x.com")
        db_session.add(other_user)
        db_session.flush()
        other_project = make_project(other_user.id, name="Other", slug="other")
        db_session.add(other_project)
        db_session.flush()

        _make_bare_subject(db_session, project_id=project.id, subject_code="mine")
        _make_bare_subject(db_session, project_id=other_project.id, subject_code="theirs")

        rows, total = psr.list_subjects(db_session, project_id=project.id)
        assert total == 1
        assert rows[0][0].subject_code == "mine"


# ===========================================================================
# Repository tests: get_subject_with_participant
# ===========================================================================


class TestGetSubjectWithParticipant:
    def test_returns_none_when_missing(
        self, db_session: Session, project: Project
    ) -> None:
        result = psr.get_subject_with_participant(
            db_session, project_id=project.id, subject_id=uuid4()
        )
        assert result is None

    def test_returns_subject_and_participant_id(
        self, db_session: Session, project: Project
    ) -> None:
        participant = make_participant_chain(
            db_session, project_id=project.id, subject_code="enrolled"
        )

        result = psr.get_subject_with_participant(
            db_session, project_id=project.id, subject_id=participant.project_subject_id
        )
        assert result is not None
        subject, p_id = result
        assert subject.subject_code == "enrolled"
        assert p_id == participant.id

    def test_returns_none_participant_for_bare_subject(
        self, db_session: Session, project: Project
    ) -> None:
        bare = _make_bare_subject(db_session, project_id=project.id, subject_code="bare")

        result = psr.get_subject_with_participant(
            db_session, project_id=project.id, subject_id=bare.id
        )
        assert result is not None
        subject, p_id = result
        assert subject.id == bare.id
        assert p_id is None

    def test_eagerly_loads_identities(
        self, db_session: Session, project: Project
    ) -> None:
        s = _make_bare_subject(db_session, project_id=project.id, subject_code="s1")
        _make_identity(db_session, project_id=project.id, subject_id=s.id, email="a@x.com")
        _make_identity(db_session, project_id=project.id, subject_id=s.id, email="b@x.com")

        result = psr.get_subject_with_participant(
            db_session, project_id=project.id, subject_id=s.id
        )
        assert result is not None
        subject, _ = result
        assert len(subject.identities) == 2


# ===========================================================================
# Service tests
# ===========================================================================


class TestSubjectService:
    def test_get_subject_raises_not_found(
        self, db_session: Session, project: Project
    ) -> None:
        import pytest

        from app.domain.errors import SubjectNotFoundError

        with pytest.raises(SubjectNotFoundError):
            subject_service.get_subject(
                db_session, project_id=project.id, subject_id=uuid4()
            )

    def test_update_subject_code(
        self, db_session: Session, project: Project
    ) -> None:
        s = _make_bare_subject(db_session, project_id=project.id, subject_code="old-code")

        subject, _ = subject_service.update_subject(
            db_session,
            project_id=project.id,
            subject_id=s.id,
            data=_make_update_request("new-code"),
        )
        assert subject.subject_code == "new-code"


def _make_update_request(subject_code: str):
    from app.schema.api.requests.subjects import UpdateSubjectRequest

    return UpdateSubjectRequest(subject_code=subject_code)


# ===========================================================================
# Response shape: security tests
# ===========================================================================


class TestResponseShapeSecurity:
    """Verify API response schemas never expose sensitive fields."""

    def test_subject_identity_response_excludes_user_id(
        self, db_session: Session, project: Project
    ) -> None:
        from app.schema.api.responses.subjects import SubjectIdentityResponse

        s = _make_bare_subject(db_session, project_id=project.id)
        identity = _make_identity(
            db_session, project_id=project.id, subject_id=s.id, email="x@y.com"
        )

        response = SubjectIdentityResponse.model_validate(identity)
        dumped = response.model_dump(mode="json")
        assert "user_id" not in dumped
        assert "token_hash" not in dumped

    def test_subject_list_response_excludes_tokens(
        self, db_session: Session, project: Project
    ) -> None:
        from app.schema.api.responses.subjects import SubjectResponse

        s = _make_bare_subject(db_session, project_id=project.id, subject_code="s1")
        _make_identity(db_session, project_id=project.id, subject_id=s.id, email="a@b.com")

        rows, _ = psr.list_subjects(db_session, project_id=project.id)
        response = SubjectResponse.model_validate(rows[0])
        dumped = response.model_dump(mode="json")

        sensitive_fields = {"user_id", "token_hash", "tokens", "session_locator", "wrapped_dek"}
        assert not sensitive_fields.intersection(dumped.keys())

    def test_subject_detail_response_excludes_sensitive_identity_fields(
        self, db_session: Session, project: Project
    ) -> None:
        from app.schema.api.responses.subjects import SubjectDetailResponse

        s = _make_bare_subject(db_session, project_id=project.id, subject_code="s1")
        _make_identity(db_session, project_id=project.id, subject_id=s.id, email="a@b.com")

        result = psr.get_subject_with_participant(
            db_session, project_id=project.id, subject_id=s.id
        )
        assert result is not None
        response = SubjectDetailResponse.model_validate(result)
        dumped = response.model_dump(mode="json")

        for identity in dumped["identities"]:
            assert "user_id" not in identity
            assert "token_hash" not in identity
            assert "project_subject_id" not in identity
