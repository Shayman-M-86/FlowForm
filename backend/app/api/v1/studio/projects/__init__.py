from logging import getLogger

from flask import Blueprint

from app.core.extensions import auth
from app.services.content import ContentService
from app.services.members import MembersService
from app.services.participants import ParticipantService
from app.services.projects import ProjectService
from app.services.roles import RolesService
from app.services.subjects import SubjectService
from app.services.survey_links import SurveyLinkService
from app.services.surveys import SurveyService
from app.services.users import UserService

logger = getLogger(__name__)

studio_projects_bp = Blueprint("studio_projects_v1", __name__)

users_service = UserService()
content_svc = ContentService()
members_service = MembersService()
participant_service = ParticipantService()
project_service = ProjectService()
roles_service = RolesService()
survey_link_service = SurveyLinkService()
subject_service = SubjectService()
survey_service = SurveyService()

from app.api.v1.studio.projects import (  # noqa: E402, I001
    invitations,
    members,
    participants,
    roles,
    routes,
    subjects,
)
from app.api.v1.studio import surveys  # noqa: E402
