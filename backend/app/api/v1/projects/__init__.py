from logging import getLogger

from flask import Blueprint

from app.core.extensions import auth
from app.services.content import ContentService
from app.services.projects import ProjectService
from app.services.public_links import SurveyLinkService
from app.services.submissions import SubmissionQueryService
from app.services.surveys import SurveyService
from app.services.users import UserService

logger = getLogger(__name__)

projects_bp = Blueprint("projects_v1", __name__)

users_service = UserService()
content_svc = ContentService()
project_service = ProjectService()
survey_link_service = SurveyLinkService()
survey_service = SurveyService()
submission_query_service = SubmissionQueryService()

# Import sub-modules to register their routes on projects_bp
from app.api.v1.projects import content, core, public_links, submissions, surveys, versions  # noqa: E402
