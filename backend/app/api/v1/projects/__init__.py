from logging import getLogger

from flask import Blueprint

from app.core.extensions import auth
from app.services.content import ContentService
from app.services.members import MembersService
from app.services.participants import ParticipantService
from app.services.projects import ProjectService
from app.services.roles import RolesService
from app.services.survey_links import SurveyLinkService
from app.services.surveys import SurveyService
from app.services.users import UserService

logger = getLogger(__name__)

projects_bp = Blueprint("projects_v1", __name__)

users_service = UserService()
content_svc = ContentService()
members_service = MembersService()
participant_service = ParticipantService()
project_service = ProjectService()
roles_service = RolesService()
survey_link_service = SurveyLinkService()
survey_service = SurveyService()

# Import sub-modules to register their routes on projects_bp
from app.api.v1.projects import (  # noqa: E402, I001
    content, core, members, participants, public_links, roles, survey_responses,
    survey_members, survey_roles, surveys, versions,
)
