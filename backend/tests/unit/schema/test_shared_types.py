"""Shared identities retain nominal checking, boundary validation, and SQL storage."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Annotated, NewType, get_args, get_origin
from uuid import UUID

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError
from sqlalchemy import BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID as SQLUuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.type_mapping import IDENTITY_TYPE_MAP
from app.schema import types
from app.schema.types import Auth0UserId, ProjectId, ProjectName, UserId


def identities():
    for name, alias in vars(types).items():
        if name.startswith("_") or not hasattr(alias, "__value__"):
            continue
        value = alias.__value__
        if get_origin(value) is Annotated:
            underlying = get_args(value)[0]
            if isinstance(underlying, NewType):
                yield name, alias, underlying


@pytest.mark.parametrize(
    ("name", "alias", "nominal"), identities(), ids=lambda value: getattr(value, "__name__", str(value))
)
def test_every_nominal_identity_has_a_storage_mapping_and_boundary_validation(name, alias, nominal):
    assert nominal.__name__ == "_" + name
    assert alias in IDENTITY_TYPE_MAP
    adapter = TypeAdapter(alias)
    primitive = nominal.__supertype__
    if primitive is int:
        assert IDENTITY_TYPE_MAP[alias] is BigInteger
        for valid in [1, 2**63 - 1]:
            assert adapter.validate_python(valid) == valid
        for invalid in [0, -1, 2**63]:
            with pytest.raises(ValidationError):
                adapter.validate_python(invalid)
    elif primitive is UUID:
        assert isinstance(IDENTITY_TYPE_MAP[alias], SQLUuid)
        raw = "10000000-0000-4000-8000-000000000001"
        parsed = adapter.validate_python(raw)
        assert parsed == UUID(raw)
        assert json.loads(adapter.dump_json(parsed)) == raw
        with pytest.raises(ValidationError):
            adapter.validate_python("invalid")
    else:
        assert alias is Auth0UserId and primitive is str
        assert IDENTITY_TYPE_MAP[alias] is Text
        assert adapter.validate_python("oidc|Opaque_VALUE") == "oidc|Opaque_VALUE"
        for invalid in ["", "x" * 256]:
            with pytest.raises(ValidationError):
                adapter.validate_python(invalid)


def test_shared_constraints_do_not_leak_property_metadata():
    class Pair(BaseModel):
        project_id: ProjectId
        user_id: UserId

    schema = Pair.model_json_schema()
    project = schema["$defs"]["ProjectId"]
    user = schema["$defs"]["UserId"]
    assert project["minimum"] == user["minimum"] == 1
    assert project["maximum"] == user["maximum"] == 2**63 - 1
    assert project["description"] == "Project identity"
    assert user["description"] == "Internal users.id database identity"
    assert Pair.model_validate({"project_id": 1, "user_id": 2}).model_dump() == {"project_id": 1, "user_id": 2}
    assert types.DATABASE_ID_CONSTRAINTS.description is None


def test_named_types_preserve_string_normalization_and_bounds():
    assert TypeAdapter(ProjectName).validate_python("  Research  ") == "Research"
    assert TypeAdapter(types.EmailAddress).validate_python(" Person@EXAMPLE.com ") == "person@example.com"
    assert TypeAdapter(types.ContentText).validate_python("  content  ") == "  content  "
    for alias, invalid in [(ProjectName, " "), (ProjectName, "x" * 101), (types.InputPlaceholder, "x" * 201)]:
        with pytest.raises(ValidationError):
            TypeAdapter(alias).validate_python(invalid)


def test_sqlalchemy_infers_nominal_identity_storage_without_pydantic_assignment_validation():
    class Base(DeclarativeBase):
        type_annotation_map = IDENTITY_TYPE_MAP

    class Example(Base):
        __tablename__ = "identity_mapping_probe"
        id: Mapped[ProjectId] = mapped_column(primary_key=True)
        user_id: Mapped[UserId | None]

    assert isinstance(Example.__table__.c.id.type, BigInteger)
    assert isinstance(Example.__table__.c.user_id.type, BigInteger)
    assert Example.__table__.c.user_id.nullable
    value = TypeAdapter(ProjectId).validate_python(12)
    assert Example(id=value).id == 12
    # SQLAlchemy construction intentionally does not run Pydantic bounds.
    unchecked = types._ProjectId(-1)
    assert Example(id=unchecked).id == -1


def test_pyright_distinguishes_identities_and_accepts_validated_boundary_values(tmp_path):
    checker = shutil.which("pyright")
    assert checker is not None, "Install the backend dev dependencies to run static identity checks"
    probe = tmp_path / "identity_probe.py"
    probe.write_text(
        "from pydantic import TypeAdapter\n"
        "from app.schema.types import ProjectId, UserId, SurveyFieldUuid, ClientMutationId\n"
        "from app.schema.orm.core.project_participant import ProjectParticipant\n"
        "def project(value: ProjectId) -> ProjectId: return value\n"
        "def field(value: SurveyFieldUuid) -> SurveyFieldUuid: return value\n"
        "valid = project(TypeAdapter(ProjectId).validate_python(1))\n"
        "def wrong_user(value: UserId) -> ProjectId: return project(value)\n"
        "def wrong_uuid(value: ClientMutationId) -> SurveyFieldUuid: return field(value)\n"
        "invalid = ProjectParticipant(project_id=1, project_subject_id=None, identity_id=None)\n"
    )
    backend = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [checker, "--project", str(backend / "pyrightconfig.json"), "--outputjson", str(probe)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    report = json.loads(result.stdout)
    errors = [d for d in report["generalDiagnostics"] if d["severity"] == "error"]
    assert len(errors) == 5, errors
    messages = "\n".join(d["message"] for d in errors)
    assert '"_UserId" is not assignable to "_ProjectId"' in messages
    assert '"_ClientMutationId" is not assignable to "_SurveyFieldUuid"' in messages
    assert not any(d["range"]["start"]["line"] == 5 for d in errors)
