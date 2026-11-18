"""Shared value annotations must preserve ordinary ORM column behavior."""

import importlib
from annotationlib import Format, get_annotations
from typing import get_args

import pytest
from pydantic import ValidationError
from sqlalchemy import BigInteger, Text

from app.schema.api.requests.projects import SendInvitationRequest
from app.schema.models.common.types import EmailAddress, Slug, Timestamp
from app.schema.models.identity.types import Auth0UserId, UserId
from app.schema.models.projects.types import InvitationMessage, ProjectId, ProjectInvitationId, ProjectRoleId
from app.schema.models.survey.types import SurveyId, SurveyTitle
from app.schema.orm.core.invitation import ProjectInvitation
from app.schema.orm.core.project import Project
from app.schema.orm.core.survey import Survey
from app.schema.orm.core.user import User


@pytest.mark.parametrize(
    ("model", "field", "value_type"),
    [
        (ProjectInvitation, "id", ProjectInvitationId),
        (ProjectInvitation, "project_id", ProjectId),
        (ProjectInvitation, "invited_email", EmailAddress),
        (ProjectInvitation, "invite_message", InvitationMessage | None),
        (ProjectInvitation, "role_id", ProjectRoleId | None),
        (ProjectInvitation, "invited_by_user_id", UserId | None),
        (ProjectInvitation, "created_at", Timestamp),
        (Project, "slug", Slug),
        (User, "id", UserId),
        (User, "auth0_user_id", Auth0UserId),
        (User, "email", EmailAddress),
        (Survey, "id", SurveyId),
        (Survey, "title", SurveyTitle),
    ],
)
def test_orm_annotation_references_shared_type(model, field, value_type):
    annotation = get_annotations(model, format=Format.STRING)[field]
    while isinstance(annotation, str):
        annotation = eval(annotation, vars(importlib.import_module(model.__module__)))
    assert get_args(annotation)[0] == value_type


def test_email_annotation_does_not_add_orm_validation():
    row = ProjectInvitation(project_id=1, invited_email="not an email", token_hash="test-hash")
    assert row.invited_email == "not an email"
    row.invited_email = "  UNNORMALIZED@example.com  "
    assert row.invited_email == "  UNNORMALIZED@example.com  "
    with pytest.raises(ValidationError):
        SendInvitationRequest(email="not an email")
    assert SendInvitationRequest(email="  Person@EXAMPLE.com ").email == "person@example.com"


def test_invitation_storage_configuration_is_preserved():
    table = ProjectInvitation.__table__
    assert isinstance(table.c.id.type, BigInteger)
    assert table.c.id.identity is not None
    assert isinstance(table.c.invited_email.type, Text)
    assert table.c.invited_email.nullable is False
    assert table.c.role_id.nullable is True
    assert table.c.created_at.server_default is not None
    assert table.c.invited_email.default is None
