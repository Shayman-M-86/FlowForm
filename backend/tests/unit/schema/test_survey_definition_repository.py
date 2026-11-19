"""Whole-document persistence, scoped reads, and transaction ownership."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import JSON, BigInteger, Integer, MetaData, Table, create_engine, event, text
from sqlalchemy.dialects.postgresql import JSONB, dialect
from sqlalchemy.orm import Session

from app.db.json_types import SurveyDefinitionJSONB
from app.repositories import surveys_repo
from app.schema.models.survey_document import SurveyDefinition
from app.schema.orm.core.project import Project
from app.schema.orm.core.response_store import ResponseStore
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.user import User
from app.schema.types import ProjectId, SurveyId


class SQLiteDefinitionJSON(SurveyDefinitionJSONB):
    """Run the same conversion hooks over JSON in the isolated SQLite fixture."""

    impl = JSON
    cache_ok = True


def definition(version_id: int = 11) -> SurveyDefinition:
    return SurveyDefinition.model_validate(
        {
            "id": "study",
            "versionId": version_id,
            "revision": 1,
            "title": "Study",
            "projectName": "Research",
            "status": "draft",
            "document": {
                "sections": [
                    {
                        "id": "section",
                        "title": "Details",
                        "blocks": [
                            {
                                "id": "birth_date",
                                "type": "input",
                                "field": {
                                    "id": "birth_date",
                                    "uuid": "10000000-0000-4000-8000-000000000001",
                                    "prompt": "Date?",
                                    "interaction": {"kind": "date"},
                                    "answerSpec": {
                                        "type": "date",
                                        "required": True,
                                        "constraints": {"min": "2020-01-01"},
                                    },
                                },
                            }
                        ],
                    }
                ]
            },
        }
    )


@pytest.fixture
def db() -> Iterator[Session]:
    metadata = MetaData()
    for model in (User, Project, ResponseStore, Survey, SurveyVersion):
        source = model.__table__
        assert isinstance(source, Table)
        table = source.to_metadata(metadata)
        for column in table.columns:
            if isinstance(column.type, BigInteger):
                column.type = column.type.with_variant(Integer(), "sqlite")
            elif isinstance(column.type, SurveyDefinitionJSONB):
                # Adapt only the cloned DDL; keep the production conversion hooks.
                column.type = SQLiteDefinitionJSON()
            elif isinstance(column.type, JSONB):
                column.type = JSON()
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    try:
        metadata.create_all(engine)
        with Session(engine) as session:
            session.execute(
                metadata.tables["projects"].insert(),
                [{"id": 1, "name": "Research", "slug": "research"}, {"id": 2, "name": "Other", "slug": "other"}],
            )
            session.execute(
                metadata.tables["surveys"].insert(),
                [{"id": 1, "project_id": 1, "title": "Study"}, {"id": 2, "project_id": 2, "title": "Other"}],
            )
            session.execute(
                metadata.tables["survey_versions"].insert(),
                [
                    {"id": 11, "survey_id": 1, "version_number": 1, "definition": definition(), "deleted_at": None},
                    {"id": 12, "survey_id": 1, "version_number": 2, "definition": None, "deleted_at": None},
                    {
                        "id": 13,
                        "survey_id": 1,
                        "version_number": 3,
                        "definition": definition(13),
                        "deleted_at": datetime(2020, 1, 1, tzinfo=UTC),
                    },
                ],
            )
            session.commit()
            yield session
    finally:
        engine.dispose()


def read(db: Session, project_id: int = 1, survey_id: int = 1, version_number: int = 1) -> SurveyDefinition | None:
    return surveys_repo.get_definition(
        db,
        TypeAdapter(ProjectId).validate_python(project_id),
        TypeAdapter(SurveyId).validate_python(survey_id),
        version_number,
    )


def test_definition_round_trips_as_model_and_stores_json(db):
    loaded = read(db)
    assert isinstance(loaded, SurveyDefinition)
    assert loaded == definition()
    raw = db.execute(text("SELECT definition FROM survey_versions WHERE id = 11")).scalar_one()
    stored = json.loads(raw)
    field = stored["document"]["sections"][0]["blocks"][0]["field"]
    assert field["uuid"] == "10000000-0000-4000-8000-000000000001"
    assert field["answerSpec"]["constraints"]["min"] == "2020-01-01"
    assert stored["versionId"] == 11


@pytest.mark.parametrize(("project_id", "survey_id", "number"), [(2, 1, 1), (1, 2, 1), (1, 1, 99), (1, 1, 3)])
def test_definition_reads_respect_scope_and_soft_deletion(db, project_id, survey_id, number):
    assert read(db, project_id, survey_id, number) is None


def test_empty_draft_has_no_definition(db):
    assert read(db, version_number=2) is None


def test_read_returns_an_independent_snapshot(db):
    loaded = read(db)
    assert loaded is not None
    loaded.document.sections[0].title = "Edited"
    untouched = read(db)
    assert untouched is not None
    assert untouched.document.sections[0].title == "Details"


def test_replace_definition_flushes_without_committing_and_preserves_metadata(db, monkeypatch):
    version = db.get(SurveyVersion, 11)
    assert version is not None
    created_at = version.created_at
    payload = definition().model_copy(update={"title": "Updated", "revision": 2}, deep=True)
    commit = Mock(wraps=db.commit)
    monkeypatch.setattr(db, "commit", commit)
    assert surveys_repo.update_definition(db, version, payload) is version
    commit.assert_not_called()
    payload.title = "Changed by caller"
    assert version.definition is not None and version.definition.title == "Updated"
    db.commit()
    db.expire_all()
    stored = read(db)
    assert stored is not None and stored.title == "Updated" and stored.revision == 2
    assert version.status == "draft" and version.version_number == 1
    assert version.created_at == created_at


def test_explicit_save_persists_in_place_model_edits(db):
    version = db.get(SurveyVersion, 11)
    assert version is not None and version.definition is not None
    version.definition.title = "Nested change"
    surveys_repo.update_definition(db, version, version.definition)
    db.commit()
    db.expire_all()
    stored = read(db)
    assert stored is not None and stored.title == "Nested change"


def test_caller_can_roll_back_definition_replacement(db):
    version = db.get(SurveyVersion, 11)
    assert version is not None
    surveys_repo.update_definition(db, version, definition().model_copy(update={"title": "Uncommitted"}))
    db.rollback()
    stored = read(db)
    assert stored is not None and stored.title == "Study"


def test_definition_type_preserves_jsonb_and_rejects_invalid_stored_shape():
    value_type = SurveyDefinitionJSONB()
    assert str(value_type.compile(dialect=dialect())) == "JSONB"
    assert value_type.process_result_value(None, dialect()) is None
    with pytest.raises(ValidationError):
        value_type.process_result_value({"nodes": []}, dialect())
