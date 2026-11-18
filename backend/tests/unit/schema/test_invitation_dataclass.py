"""Single-model pilot for SQLAlchemy's generated dataclass constructor."""

import inspect
from dataclasses import fields, is_dataclass
from typing import Any, cast

import pytest
from pydantic import TypeAdapter
from sqlalchemy import BigInteger, Integer, MetaData, create_engine, event
from sqlalchemy.orm import Session

from app.schema.orm.core.invitation import ProjectInvitation
from app.schema.orm.core.project import Project, ProjectRole
from app.schema.orm.core.user import User
from app.schema.types import ProjectId, ProjectRoleId, UserId


def test_invitation_has_generated_keyword_only_constructor():
    assert is_dataclass(ProjectInvitation)
    signature = inspect.signature(ProjectInvitation)
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in signature.parameters.values())
    required = {name for name, p in signature.parameters.items() if p.default is inspect.Parameter.empty}
    assert required == {"project_id", "invited_email", "token_hash"}
    excluded = {f.name for f in fields(ProjectInvitation) if not f.init}
    assert excluded == {"id", "created_at", "project", "role", "invited_by", "accepted_by"}
    invitation = ProjectInvitation(
        project_id=TypeAdapter(ProjectId).validate_python(1), invited_email="person@example.com", token_hash="hash"
    )
    assert invitation.status == "pending" and invitation.role_id is None
    assert "id" not in invitation.__dict__ and "created_at" not in invitation.__dict__
    assert "role" not in invitation.__dict__
    with pytest.raises(TypeError, match="unexpected keyword"):
        cast(Any, ProjectInvitation)(project_id=1, invited_email="person@example.com", token_hash="hash", typo=True)


def test_dataclass_pilot_does_not_change_orm_identity_equality():
    one = ProjectInvitation(
        project_id=TypeAdapter(ProjectId).validate_python(1), invited_email="person@example.com", token_hash="hash"
    )
    two = ProjectInvitation(
        project_id=TypeAdapter(ProjectId).validate_python(1), invited_email="person@example.com", token_hash="hash"
    )
    assert one == one and one != two
    assert isinstance(hash(one), int)
    assert "token_hash" not in repr(one)


def test_invitation_persistence_and_relationships_on_sqlite():
    # Clone only the test schema: SQLite generates identities for INTEGER PKs.
    # The production metadata retains its BIGINT definitions.
    metadata = MetaData()
    for model in [User, Project, ProjectRole, ProjectInvitation]:
        table = model.__table__.to_metadata(metadata)
        for column in table.columns:
            if isinstance(column.type, BigInteger):
                column.type = column.type.with_variant(Integer(), "sqlite")
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        metadata.create_all(engine)
        with Session(engine) as db:
            db.execute(
                User.__table__.insert().values(
                    id=1, auth0_user_id="auth0|pilot", email="person@example.com", public_id="abcdefgh"
                )
            )
            db.execute(Project.__table__.insert().values(id=1, name="Pilot", slug="pilot", created_by_user_id=1))
            db.execute(ProjectRole.__table__.insert().values(id=1, project_id=1, name="Pilot role"))
            invitation = ProjectInvitation(
                project_id=TypeAdapter(ProjectId).validate_python(1),
                invited_email="person@example.com",
                token_hash="pilot-hash",
                role_id=TypeAdapter(ProjectRoleId).validate_python(1),
                invited_by_user_id=TypeAdapter(UserId).validate_python(1),
            )
            db.add(invitation)
            db.flush()
            assert invitation.id is not None and invitation.created_at is not None
            assert invitation.role_id == 1
            assert invitation.role.name == "Pilot role"
            assert invitation.project.name == "Pilot" and invitation.invited_by.email == "person@example.com"
            invitation.status = "declined"
            identity = invitation.id
            db.commit()
        with Session(engine) as db:
            loaded = db.get(ProjectInvitation, identity)
            assert loaded is not None and loaded.status == "declined"
            assert loaded.role_id is not None and loaded.role.name == "Pilot role"
    finally:
        engine.dispose()
