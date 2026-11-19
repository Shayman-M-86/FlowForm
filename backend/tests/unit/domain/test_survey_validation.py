"""Pydantic owns data validity; survey rules retain stored-state requirements."""

import pytest
from pydantic import TypeAdapter, ValidationError

from app.domain import survey_rules
from app.domain.errors import (
    SurveyNoResponseStoreError,
    SurveyNotAccessibleError,
    SurveyNotPublishedError,
    SurveyVisibilityMismatchError,
)
from app.schema.api.requests.submission_sessions import SaveSubmissionSessionAnswerRequest
from app.schema.api.requests.surveys import CreateSurveyRequest
from app.schema.models.common.survey_access import NonPublicSurveyAccess, PublicSurveyAccess
from app.schema.models.survey_document import SurveyDefinition
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.types import ProjectId, ResponseStoreId, SurveyId

ANSWER = TypeAdapter(SaveSubmissionSessionAnswerRequest)
CREATE = TypeAdapter(CreateSurveyRequest)


def definition():
    return {
        "id": "survey",
        "versionId": 11,
        "revision": 1,
        "title": "Survey",
        "projectName": "Research",
        "status": "draft",
        "document": {"sections": []},
    }


def answer():
    return {
        "field_uuid": "10000000-0000-4000-8000-000000000001",
        "client_mutation_id": "20000000-0000-4000-8000-000000000001",
        "state": "answered",
        "answer_spec": {"type": "integer", "required": True, "constraints": {"min": 1, "max": 5}},
        "answer_value": 3,
    }


def survey():
    return Survey(project_id=TypeAdapter(ProjectId).validate_python(1), title="Survey")


def test_definition_validation_uses_canonical_model():
    assert isinstance(survey_rules.validate_definition(definition()), SurveyDefinition)
    with pytest.raises(ValidationError):
        survey_rules.validate_definition(definition() | {"revision": 0})
    with pytest.raises(ValidationError):
        survey_rules.validate_definition({"nodes": []})


def test_answer_request_validates_specification_and_value_together():
    assert ANSWER.validate_python(answer()).answer_value == 3
    for invalid in [0, 6, 1.5, True, "three", None]:
        with pytest.raises(ValidationError):
            ANSWER.validate_python(answer() | {"answer_value": invalid})


@pytest.mark.parametrize("spec", [{"type": "unknown", "required": True}, {"family": "rating"}, None])
def test_answer_rejects_unknown_or_missing_specifications(spec):
    with pytest.raises(ValidationError):
        ANSWER.validate_python(answer() | {"answer_spec": spec})


def test_cleared_answer_omits_spec_and_value():
    payload = {k: v for k, v in answer().items() if k not in {"answer_spec", "answer_value"}}
    payload["state"] = "cleared"
    assert ANSWER.validate_python(payload).state == "cleared"
    with pytest.raises(ValidationError):
        ANSWER.validate_python(payload | {"answer_value": 3})


@pytest.mark.parametrize("visibility", ["public", "private", "link_only"])
def test_requests_and_merged_updates_share_access_models(visibility):
    slug = "public-survey" if visibility == "public" else None
    created = CREATE.validate_python({"title": "Survey", "visibility": visibility, "public_slug": slug})
    expected = PublicSurveyAccess if visibility == "public" else NonPublicSurveyAccess
    assert isinstance(created, expected)
    survey_rules.ensure_visibility_slug_coherent(visibility=created.visibility, public_slug=created.public_slug)


@pytest.mark.parametrize(
    ("visibility", "slug"), [("public", None), ("public", ""), ("private", "slug"), ("link_only", "slug")]
)
def test_access_mismatch_remains_a_domain_422(visibility, slug):
    with pytest.raises(SurveyVisibilityMismatchError) as caught:
        survey_rules.ensure_visibility_slug_coherent(visibility=visibility, public_slug=slug)
    assert caught.value.status_code == 422
    assert isinstance(caught.value.__cause__, ValidationError)


def test_published_status_still_requires_a_stored_state_check():
    version = SurveyVersion(survey_id=TypeAdapter(SurveyId).validate_python(1), version_number=1)
    ids = {"survey_id": version.survey_id, "project_id": TypeAdapter(ProjectId).validate_python(1)}
    with pytest.raises(SurveyNotPublishedError):
        survey_rules.ensure_is_published(survey=version, **ids)
    with pytest.raises(SurveyNotPublishedError):
        survey_rules.ensure_is_published(survey=None, **ids)
    version.status = "published"
    assert survey_rules.ensure_is_published(survey=version, **ids) is version


def test_public_access_still_requires_stored_visibility():
    row = survey()
    with pytest.raises(SurveyNotAccessibleError):
        survey_rules.ensure_is_publicly_accessible(survey=row)
    row.visibility = "public"
    assert survey_rules.ensure_is_publicly_accessible(survey=row) is row


def test_response_store_requirement_and_default_are_preserved():
    row = survey()
    with pytest.raises(SurveyNoResponseStoreError):
        survey_rules.ensure_has_response_store(survey=row)
    first = TypeAdapter(ResponseStoreId).validate_python(1)
    other = TypeAdapter(ResponseStoreId).validate_python(2)
    assert survey_rules.ensure_default_response_store(survey=row, default_response_store_id=first) == first
    assert survey_rules.ensure_has_response_store(survey=row) == first
    assert survey_rules.ensure_default_response_store(survey=row, default_response_store_id=other) == first
