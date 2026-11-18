"""Participant constructor shape and persistence after dataclass integration."""

import inspect
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import BigInteger, Integer, MetaData, create_engine, event
from sqlalchemy.orm import Session

from app.schema.orm.core.project import Project
from app.schema.orm.core.project_participant import ProjectParticipant
from app.schema.orm.core.project_subject import ProjectSubject, ProjectSubjectIdentity
from app.schema.orm.core.user import User


def test_participant_constructor_requires_only_its_three_identity_inputs():
    signature = inspect.signature(ProjectParticipant)
    assert set(signature.parameters) == {"project_id", "project_subject_id", "identity_id"}
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in signature.parameters.values())
    participant = ProjectParticipant(project_id=1, project_subject_id=uuid4(), identity_id=uuid4())
    assert participant.id is None and participant.created_at is None
    assert not {"project", "subject", "identity"} & participant.__dict__.keys()
    with pytest.raises(TypeError, match="unexpected keyword"):
        cast(Any, ProjectParticipant)(project_id=1, project_subject_id=uuid4(), identity_id=uuid4(), wrong_field=True)


def test_participant_persists_generated_values_and_retains_identity_foreign_keys():
    metadata = MetaData()
    for model in [User, Project, ProjectSubject, ProjectSubjectIdentity, ProjectParticipant]:
        table = model.__table__.to_metadata(metadata)
        for column in table.columns:
            if isinstance(column.type, BigInteger):
                column.type = column.type.with_variant(Integer(), "sqlite")
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def functions(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.create_function("gen_random_uuid", 0, lambda: "a" + uuid4().hex[1:])

    subject_id, identity_id = uuid4(), uuid4()
    try:
        metadata.create_all(engine)
        with Session(engine) as db:
            db.execute(
                User.__table__.insert().values(
                    id=1, auth0_user_id="auth0|test", email="a@example.com", public_id="abcdefgh"
                )
            )
            db.execute(Project.__table__.insert().values(id=1, name="Test", slug="test", created_by_user_id=1))
            db.execute(
                ProjectSubject.__table__.insert().values(id=subject_id, project_id=1, subject_code="participant")
            )
            db.execute(
                ProjectSubjectIdentity.__table__.insert().values(
                    id=identity_id,
                    project_id=1,
                    project_subject_id=subject_id,
                    identity_type="email",
                    normalized_email="a@example.com",
                )
            )
            participant = ProjectParticipant(project_id=1, project_subject_id=subject_id, identity_id=identity_id)
            db.add(participant)
            db.flush()
            assert isinstance(participant.id, UUID) and participant.created_at is not None
            assert participant.project_subject_id == subject_id and participant.identity_id == identity_id
            assert (
                participant.project.id == 1
                and participant.subject.id == subject_id
                and participant.identity.id == identity_id
            )
            saved_id = participant.id
            db.commit()
        with Session(engine) as db:
            loaded = db.get(ProjectParticipant, saved_id)
            assert loaded is not None and loaded.subject.id == subject_id and loaded.identity.id == identity_id
    finally:
        engine.dispose()
