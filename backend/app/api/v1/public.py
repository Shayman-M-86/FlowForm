from flask import Blueprint, request
from sqlalchemy import select

from app.api.utils.validation import parse
from app.core.responses import ErrorResponse, SuccessResponse
from app.db.context import get_core_db, get_response_db
from app.schema.api.requests.submissions import PublicSubmissionRequest, ResolveTokenRequest
from app.schema.api.responses.public_links import PublicLinkOut
from app.schema.api.responses.submissions import AnswerOut, CoreSubmissionOut, LinkedSubmissionOut
from app.schema.api.responses.surveys import SurveyOut, SurveyVersionOut
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.repository import public_link_repo as link_svc
from app.repositories import surveys_repo as survey_svc
from app.services.submission_gateway import SubmissionGateway
from app.services.public_links import PublicLinkService
from app.schema.api.responses.public_links import ResolveLinkOut


public_bp = Blueprint("public_v1", __name__)

_gateway = SubmissionGateway()
public_link_service = PublicLinkService()


@public_bp.route("/surveys/<string:public_slug>", methods=["GET"])
def get_public_survey(public_slug: str):
    db = get_core_db()
    survey = db.scalar(
        select(Survey).where(
            Survey.public_slug == public_slug,
            Survey.visibility == "public",
        )
    )
    if survey is None:
        return ErrorResponse.return_it("Survey not found", "NOT_FOUND", status_code=404)

    published_version = None
    if survey.published_version_id is not None:
        published_version = db.scalar(select(SurveyVersion).where(SurveyVersion.id == survey.published_version_id))

    return SuccessResponse.return_it(
        data={
            "survey": SurveyOut.model_validate(survey).model_dump(mode="json"),
            "published_version": (
                SurveyVersionOut.model_validate(published_version).model_dump(mode="json")
                if published_version
                else None
            ),
        }
    )


@public_bp.route("/links/resolve", methods=["POST"])
def resolve_link():
    payload = parse(ResolveTokenRequest, request)

    core_db = get_core_db()

    result = public_link_service.resolve_link(core_db,payload=payload)
    response = ResolveLinkOut(
        link=PublicLinkOut.model_validate(result.link),
        survey=SurveyOut.model_validate(result.survey),
        published_version=SurveyVersionOut.model_validate(result.published_version),
    )

    return response.model_dump(mode="json"), 200


@public_bp.route("/submissions", methods=["POST"])
def create_public_submission():
    core_db = get_core_db()
    response_db = get_response_db()

    data: PublicSubmissionRequest = parse(PublicSubmissionRequest, request)

    link = link_svc.resolve_token(core_db, data.public_token)
    if link is None:
        return ErrorResponse.return_it("Invalid or unknown token", "NOT_FOUND", status_code=404)
    if not link.is_active:
        return ErrorResponse.return_it("This link is inactive", "LINK_INACTIVE", status_code=403)
    if not link.allow_response:
        return ErrorResponse.return_it("This link does not allow submissions", "LINK_NO_RESPONSE", status_code=403)

    from datetime import UTC, datetime

    if link.expires_at is not None and link.expires_at < datetime.now(UTC):
        return ErrorResponse.return_it("This link has expired", "LINK_EXPIRED", status_code=403)

    survey = link.survey
    if survey.default_response_store_id is None:
        return ErrorResponse.return_it(
            "Survey has no default response store configured", "INVALID_REQUEST", status_code=400
        )

    try:
        linked = _gateway.create_linked_submission(
            core_db,
            response_db,
            project_id=survey.project_id,
            survey_id=survey.id,
            survey_version_id=data.survey_version_id,
            response_store_id=survey.default_response_store_id,
            submission_channel="public_link",
            public_link_id=link.id,
            is_anonymous=data.is_anonymous,
            started_at=data.started_at,
            submitted_at=data.submitted_at,
            answers=[a.model_dump() for a in data.answers],
            metadata=data.metadata,
        )
    except Exception as exc:
        return ErrorResponse.return_it(str(exc), "SUBMISSION_FAILED", status_code=500)

    return SuccessResponse.return_it(
        data=LinkedSubmissionOut(
            core=CoreSubmissionOut.model_validate(linked.core_submission),
            answers=[AnswerOut.model_validate(a) for a in linked.answers],
        ).model_dump(mode="json"),
        status_code=201,
    )
