from logging import getLogger

from flask import Blueprint, request

from app.api.utils.validation import parse, parse_query
from app.core.extensions import auth
from app.db.context import get_core_db, get_response_db
from app.schema.api.requests.public_links import ResolveTokenRequest
from app.schema.api.requests.submissions.create import (
    LinkSubmissionRequest,
    SlugSubmissionRequest,
)
from app.schema.api.requests.surveys import ListPublicSurveysRequest
from app.schema.api.responses.public_links import PublicLinkOut, ResolveLinkOut
from app.schema.api.responses.submissions import AnswerOut, CoreSubmissionOut, LinkedSubmissionOut
from app.schema.api.responses.surveys import PaginatedPublicSurveysOut, PublicSurveyOut, SurveyOut, SurveyVersionOut
from app.services.public_links import SurveyLinkService
from app.services.public_surveys import PublicSurveyService
from app.services.submissions import SubmissionIntakeService
from app.services.users import UserService

logger = getLogger(__name__)

public_bp = Blueprint("public_v1", __name__)

users_service = UserService()
survey_link_service = SurveyLinkService()
submission_intake_service = SubmissionIntakeService()
public_survey_service = PublicSurveyService()


@public_bp.route("/surveys", methods=["GET"])
def list_public_surveys():
    params = parse_query(ListPublicSurveysRequest, request)
    core_db = get_core_db()

    result = public_survey_service.list_public_surveys(core_db, page=params.page, page_size=params.page_size)
    response = PaginatedPublicSurveysOut(
        items=[SurveyOut.model_validate(s) for s in result.surveys],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )
    return response.model_dump(mode="json"), 200


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
@auth.require_auth()
def resolve_link():
    payload = parse_query(ResolveTokenRequest, request)

    core_db = get_core_db()

    user = users_service.get_user_by_sub(db=core_db, auth0_user_id=auth.get_current_user_sub())
    result = survey_link_service.resolve_link(core_db, payload=payload, actor=user)
    response = ResolveLinkOut(
        link=PublicLinkOut.model_validate(result.link),
        survey=SurveyOut.model_validate(result.survey),
        published_version=SurveyVersionOut.model_validate(result.published_version),
    )

    return response.model_dump(mode="json"), 200


@public_bp.route("/submissions/slug", methods=["POST"])
@auth.optional_auth()
def create_slug_submission():
    payload = parse(SlugSubmissionRequest, request)
    core_db = get_core_db()
    response_db = get_response_db()
    submitted_by_user_id = None
    current_sub = auth.get_optional_current_user_sub()
    if current_sub is not None:
        submitted_by_user_id = users_service.get_user_by_sub(db=core_db, auth0_user_id=current_sub).id

    linked = submission_intake_service.create_slug_submission(
        core_db,
        response_db,
        payload=payload,
        submitted_by_user_id=submitted_by_user_id,
    )
    response = LinkedSubmissionOut(
        core=CoreSubmissionOut.from_submission(linked.core_submission),
        answers=[AnswerOut.model_validate(a) for a in linked.answers],
    )
    return response.model_dump(mode="json"), 201


@public_bp.route("/submissions/link", methods=["POST"])
@auth.require_auth()
def create_link_submission():
    payload = parse(LinkSubmissionRequest, request)
    core_db = get_core_db()
    response_db = get_response_db()
    user = users_service.get_user_by_sub(db=core_db, auth0_user_id=auth.get_current_user_sub())
    linked = submission_intake_service.create_link_submission(
        core_db,
        response_db,
        payload=payload,
        actor=user,
    )
    response = LinkedSubmissionOut(
        core=CoreSubmissionOut.from_submission(linked.core_submission),
        answers=[AnswerOut.model_validate(a) for a in linked.answers],
    )
    return response.model_dump(mode="json"), 201
