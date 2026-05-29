from flask import request

from app.api.utils.validation import parse_query
from app.api.v1.projects import projects_bp, submission_query_service, users_service
from app.core.extensions import auth
from app.db.context import get_core_db, get_response_db
from app.openapi import openapi_route
from app.schema.api.requests.submissions.query import GetSubmissionRequest, ListSubmissionsRequest
from app.schema.api.responses.submissions import (
    AnswerResponses,
    CoreSubmissionResponses,
    LinkedSubmissionResponses,
    PaginatedSubmissionsResponses,
)
from app.schema.orm.core.user import User


@openapi_route(
    summary="List submissions",
    query_model=ListSubmissionsRequest,
    response_model=PaginatedSubmissionsResponses,
    tags=["Submissions"],
)
@projects_bp.route("/<bint:project_id>/submissions", methods=["GET"])
@auth.require_auth()
def list_submissions(project_id: int):
    payload = parse_query(ListSubmissionsRequest, request)
    core_db = get_core_db()
    user: User = users_service.get_user_by_sub(db=core_db, auth0_user_id=auth.get_current_user_sub())

    items, total = submission_query_service.list_submissions(
        db=core_db,
        project_id=project_id,
        actor=user,
        payload=payload,
    )

    response = PaginatedSubmissionsResponses(
        items=[CoreSubmissionResponses.model_validate(s) for s in items],
        page=payload.page,
        page_size=payload.page_size,
        total=total,
    )

    return response.model_dump(mode="json"), 200


@openapi_route(
    summary="Get submission",
    query_model=GetSubmissionRequest,
    response_model=LinkedSubmissionResponses,
    tags=["Submissions"],
)
@projects_bp.route("/<bint:project_id>/submissions/<bint:submission_id>", methods=["GET"])
@auth.require_auth()
def get_submission(project_id: int, submission_id: int):
    payload = parse_query(GetSubmissionRequest, request)
    core_db = get_core_db()
    response_db = get_response_db()
    user: User = users_service.get_user_by_sub(db=core_db, auth0_user_id=auth.get_current_user_sub())

    linked = submission_query_service.get_submission(
        core_db=core_db,
        response_db=response_db,
        project_id=project_id,
        submission_id=submission_id,
        actor=user,
        params=payload,
    )

    response = LinkedSubmissionResponses(
        core=CoreSubmissionResponses.model_validate(linked.core_submission),
        answers=[AnswerResponses.model_validate(a) for a in linked.answers],
    )

    return response.model_dump(mode="json"), 200
