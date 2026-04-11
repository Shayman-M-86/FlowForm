from logging import getLogger

from flask import Blueprint

from app.core.extensions import auth
from app.services.content import ContentService
from app.services.projects import ProjectService
from app.services.public_links import PublicLinkService
from app.services.submissions import SubmissionService
from app.services.surveys import SurveyService
from app.services.users import UserService

logger = getLogger(__name__)

projects_bp = Blueprint("projects_v1", __name__)

users_service = UserService()
content_svc = ContentService()
project_service = ProjectService()
public_link_svc = PublicLinkService()
survey_service = SurveyService()
submission_service = SubmissionService()

# Import sub-modules to register their routes on projects_bp
from app.api.v1.projects import content, core, public_links, submissions, surveys, versions  # noqa: E402
