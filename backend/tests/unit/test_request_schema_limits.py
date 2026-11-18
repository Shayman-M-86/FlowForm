"""Contract-specific bounds live in value types, independently of global knobs."""

from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schema.api.requests.auth import BootstrapUserRequest
from app.schema.api.requests.projects import CreateProjectRequest, CreateProjectRoleRequest, SendInvitationRequest
from app.schema.api.requests.survey_access_links import (
    CreateSurveyAccessLinkRequest,
    ResolveSurveyAccessLinkTokenRequest,
)
from app.schema.api.requests.surveys import CreateSurveyRequest
from app.schema.models.projects.types import ProjectRoleId


@pytest.mark.parametrize(
    ("factory", "bound"),
    [
        (lambda v: CreateProjectRequest(name=v, slug="valid-slug"), 100),
        (lambda v: CreateProjectRoleRequest(name=v), 80),
        (lambda v: CreateProjectRequest(name="Project", slug=v), 80),
        (lambda v: CreateSurveyAccessLinkRequest(name=v), 120),
        (lambda v: ResolveSurveyAccessLinkTokenRequest(token=v), 256),
        (lambda v: BootstrapUserRequest(id_token=v), 8192),
        (lambda v: TypeAdapter(CreateSurveyRequest).validate_python({"title": v, "visibility": "private"}), 200),
        (
            lambda v: TypeAdapter(CreateSurveyRequest).validate_python(
                {
                    "title": "Survey",
                    "visibility": "public",
                    "public_slug": v,
                }
            ),
            80,
        ),
    ],
)
def test_request_string_limits_are_enforced(factory: Any, bound: int) -> None:
    factory("x" * bound)
    with pytest.raises(ValidationError):
        factory("x" * (bound + 1))


def test_invitation_email_normalization_and_validation() -> None:
    assert SendInvitationRequest(email="  USER@Example.COM  ").email == "user@example.com"
    for email in ["", "not-an-email", "missing-domain@", "@missing-local.test"]:
        with pytest.raises(ValidationError):
            SendInvitationRequest(email=email)


def test_role_identity_storage_bounds() -> None:
    adapter = TypeAdapter(ProjectRoleId)
    assert adapter.validate_python(2**63 - 1) == 2**63 - 1
    for invalid in [0, -1, 2**63]:
        with pytest.raises(ValidationError):
            adapter.validate_python(invalid)
