"""Whole-content edits must target an existing draft before any write."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.domain.errors import SurveyVersionIdNotFoundError, VersionNotEditableError, VersionRevisionConflictError
from app.schema.models.survey_document import SurveyContent
from app.schema.orm.core.survey import SurveyVersion
from app.schema.types import ProjectId, SurveyId, SurveyVersionId
from app.services import content


@pytest.fixture
def context(monkeypatch):
    version = SurveyVersion(survey_id=TypeAdapter(SurveyId).validate_python(7), version_number=1)
    version.id = TypeAdapter(SurveyVersionId).validate_python(11)
    payload = SurveyContent.model_validate({"title": "Survey", "sections": []})
    lookup = Mock(return_value=version)
    save = Mock(return_value=version)
    commit = Mock()
    monkeypatch.setattr(content.surveys_repo, "lock_version_by_id", lookup)
    monkeypatch.setattr(content.surveys_repo, "update_content", save)
    monkeypatch.setattr(content, "commit_with_err_handle", commit)
    return SimpleNamespace(
        version=version,
        payload=payload,
        lookup=lookup,
        save=save,
        commit=commit,
        db=Mock(spec=Session),
        service=content.ContentService(),
        args={
            "project_id": TypeAdapter(ProjectId).validate_python(3),
            "survey_id": version.survey_id,
            "version_id": version.id,
            "expected_revision": 0,
            "content": payload,
        },
    )


def test_editable_draft_saves_complete_definition_and_commits(context):
    result = context.service.save_content(context.db, **context.args)
    assert result == 1
    context.lookup.assert_called_once_with(
        context.db, context.args["project_id"], context.version.survey_id, context.version.id
    )
    context.save.assert_called_once_with(context.db, context.version, context.payload, 1)
    context.commit.assert_called_once_with(context.db, contexts=[context.version])


@pytest.mark.parametrize("status", ["published", "archived"])
def test_non_draft_definition_is_not_written_or_committed(context, status):
    context.version.status = status
    with pytest.raises(VersionNotEditableError):
        context.service.save_content(context.db, **context.args)
    context.save.assert_not_called()
    context.commit.assert_not_called()


def test_missing_or_out_of_scope_version_is_not_written(context):
    context.lookup.return_value = None
    with pytest.raises(SurveyVersionIdNotFoundError):
        context.service.save_content(context.db, **context.args)
    context.save.assert_not_called()
    context.commit.assert_not_called()


def test_failed_definition_save_does_not_commit(context):
    context.save.side_effect = RuntimeError("save failed")
    with pytest.raises(RuntimeError, match="save failed"):
        context.service.save_content(context.db, **context.args)
    context.commit.assert_not_called()


def test_stale_editor_cannot_overwrite_newer_content(context):
    context.version.revision = 2
    with pytest.raises(VersionRevisionConflictError) as error:
        context.service.save_content(context.db, **context.args)
    assert error.value.details["current_revision"] == 2
    context.save.assert_not_called()
    context.commit.assert_not_called()
