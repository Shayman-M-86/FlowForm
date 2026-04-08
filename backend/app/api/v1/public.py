from logging import getLogger

from flask import Blueprint, request

from app.api.utils.validation import parse, parse_query
from app.db.context import get_core_db, get_response_db
from app.schema.api.requests.public_links import ResolveTokenRequest
from app.schema.api.requests.submissions.create import PublicSubmissionRequest
from app.schema.api.responses.public_links import PublicLinkOut, ResolveLinkOut
from app.schema.api.responses.submissions import AnswerOut, CoreSubmissionOut, LinkedSubmissionOut
from app.schema.api.responses.surveys import PublicSurveyOut, SurveyOut, SurveyVersionOut
from app.services.public_links import PublicLinkService
from app.services.public_surveys import PublicSurveyService
from app.services.submissions import SubmissionService

logger = getLogger(__name__)

public_bp = Blueprint("public_v1", __name__)

public_link_service = PublicLinkService()
public_submission_service = SubmissionService()
public_survey_service = PublicSurveyService()


@public_bp.route("/surveys/<string:public_slug>", methods=["GET"])
def get_public_survey(public_slug: str):
    core_db = get_core_db()
    result = public_survey_service.get_public_survey(core_db, public_slug=public_slug)
    response = PublicSurveyOut(
        survey=SurveyOut.model_validate(result.survey),
        published_version=(
            SurveyVersionOut.model_validate(result.published_version) if result.published_version else None
        ),
    )
    return response.model_dump(mode="json"), 200


@public_bp.route("/links/resolve", methods=["GET"])
def resolve_link():
    try:
        payload = parse_query(ResolveTokenRequest, request)
    except Exception:
        payload = parse(ResolveTokenRequest, request)
    logger.info(f"Resolving public link with token: {payload.token}")

    core_db = get_core_db()

    result = public_link_service.resolve_link(core_db, payload=payload)
    response = ResolveLinkOut(
        link=PublicLinkOut.model_validate(result.link),
        survey=SurveyOut.model_validate(result.survey),
        published_version=SurveyVersionOut.model_validate(result.published_version),
    )

    return response.model_dump(mode="json"), 200


@public_bp.route("/submissions", methods=["POST"])
def create_public_submission():
    payload = parse(PublicSubmissionRequest, request)
    core_db = get_core_db()
    response_db = get_response_db()
    linked = public_submission_service.create_public_submission(core_db, response_db, payload=payload)
    response = LinkedSubmissionOut(
        core=CoreSubmissionOut.model_validate(linked.core_submission),
        answers=[AnswerOut.model_validate(a) for a in linked.answers],
    )
    return response.model_dump(mode="json"), 201
