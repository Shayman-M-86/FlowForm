from logging import getLogger

from flask import Blueprint

from app.services.public_submissions.api.session_management import SessionManagementService
from app.services.public_submissions.api.survey_resolve import SurveyResolveService
from app.services.users import UserService

logger = getLogger(__name__)

respondent_bp = Blueprint("respondent_v1", __name__)

users_service = UserService()
survey_resolve_service = SurveyResolveService()
session_management_service = SessionManagementService()

from app.api.v1.respondent import link_resolution, public_surveys, submission_sessions  # noqa: E402
