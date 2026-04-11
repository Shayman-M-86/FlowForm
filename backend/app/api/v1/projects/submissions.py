from flask import request

from app.api.utils.validation import parse, parse_query
from app.api.v1.projects import projects_bp, submission_service, users_service
from app.api.v1.projects.resolver import resolve_project_ref
from app.core.extensions import auth
from app.db.context import get_core_db, get_response_db
from app.schema.api.requests.submissions.create import CreateSubmissionRequest
from app.schema.api.requests.submissions.query import GetSubmissionRequest, ListSubmissionsRequest
from app.schema.api.responses.submissions import (
    AnswerOut,
    CoreSubmissionOut,
    LinkedSubmissionOut,
    PaginatedSubmissionsOut,
)
from app.schema.orm.core.user import User


@projects_bp.route("/<project_ref>/surveys/<int:survey_id>/submissions", methods=["POST"])
@auth.require_auth()
def create_submission(project_ref: str, survey_id: int):
    payload = parse(CreateSubmissionRequest, request)
    core_db = get_core_db()
    response_db = get_response_db()
    user: User = users_service.get_user_by_sub(db=core_db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(core_db, project_ref, user).id
    linked = submission_service.create_project_submission(
        core_db=core_db,
        response_db=response_db,
        project_id=project_id,
        survey_id=survey_id,
        payload=payload,
    )

    response = LinkedSubmissionOut(
        core=CoreSubmissionOut.model_validate(linked.core_submission),
        answers=[AnswerOut.model_validate(a) for a in linked.answers],
    )

    return response.model_dump(mode="json"), 201


@projects_bp.route("/<project_ref>/submissions", methods=["GET"])
@auth.require_auth()
def list_submissions(project_ref: str):
    payload = parse_query(ListSubmissionsRequest, request)
    core_db = get_core_db()
    user: User = users_service.get_user_by_sub(db=core_db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(core_db, project_ref, user).id

    items, total = submission_service.list_submissions(
        db=core_db,
        project_id=project_id,
        payload=payload,
    )

    response = PaginatedSubmissionsOut(
        items=[CoreSubmissionOut.model_validate(s) for s in items],
        page=payload.page,
        page_size=payload.page_size,
        total=total,
    )

    return response.model_dump(mode="json"), 200


@projects_bp.route("/<project_ref>/submissions/<int:submission_id>", methods=["GET"])
@auth.require_auth()
def get_submission(project_ref: str, submission_id: int):
    payload = parse_query(GetSubmissionRequest, request)
    core_db = get_core_db()
    response_db = get_response_db()
    user: User = users_service.get_user_by_sub(db=core_db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(core_db, project_ref, user).id

    linked = submission_service.get_submission(
        core_db=core_db,
        response_db=response_db,
        project_id=project_id,
        submission_id=submission_id,
        params=payload,
    )

    response = LinkedSubmissionOut(
        core=CoreSubmissionOut.model_validate(linked.core_submission),
        answers=[AnswerOut.model_validate(a) for a in linked.answers],
    )

    return response.model_dump(mode="json"), 200
