from flask import request
from pydantic import TypeAdapter

from app.api.utils.submission_session_cookie import (
    get_recognition_token,
    get_submission_session_token,
    set_recognition_cookie,
    set_submission_session_cookie,
)
from app.api.utils.validation import parse
from app.api.v1.respondent import respondent_bp, session_management_service, users_service
from app.core.extensions import auth
from app.db.context import get_core_db, get_response_db
from app.domain.errors import AnswerSaveError
from app.openapi import openapi_route
from app.schema.api.requests.submission_sessions import (
    SaveSubmissionSessionAnswerRequest,
    StartSubmissionSessionRequest,
    SubmissionSessionEventRequest,
)
from app.schema.api.responses.submission_sessions import (
    CompleteSubmissionSessionResponse,
    ResumeSubmissionSessionResponse,
    StartSubmissionSessionResponse,
    SubmissionSessionAnswerResponse,
)
from app.schema.types import SurveyFieldUuid


@openapi_route(
    summary="Start submission session",
    request_model=StartSubmissionSessionRequest,
    response_model=StartSubmissionSessionResponse,
    status_code=201,
    tags=["Respondent Submission Sessions"],
    auth="optional",
)
@respondent_bp.route("/submission-sessions", methods=["POST"])
@auth.optional_auth()
def start_submission_session():
    payload = parse(StartSubmissionSessionRequest, request)
    core_db = get_core_db()
    current_sub = auth.get_optional_current_user_sub()
    user = users_service.get_user_by_sub(db=core_db, auth0_user_id=current_sub) if current_sub is not None else None
    response_db = get_response_db()
    response, raw_browser_session_token, raw_recognition_token = session_management_service.start_session(
        core_db,
        response_db,
        payload=payload,
        actor=user,
        recognition_token=get_recognition_token(),
    )
    set_submission_session_cookie(raw_browser_session_token)
    if raw_recognition_token is not None:
        set_recognition_cookie(raw_recognition_token)
    return response.model_dump(mode="json"), 201


@openapi_route(
    summary="Resume current submission session",
    request_model=StartSubmissionSessionRequest,
    response_model=ResumeSubmissionSessionResponse,
    tags=["Respondent Submission Sessions"],
    auth_required=False,
)
@respondent_bp.route("/submission-sessions/current/resolve", methods=["POST"])
def resume_submission_session():
    payload = parse(StartSubmissionSessionRequest, request)
    response = session_management_service.resume_session(
        get_core_db(),
        payload=payload,
        raw_resume_token=get_submission_session_token(),
    )
    return response.model_dump(mode="json"), 200


@openapi_route(
    summary="Save submission session answer",
    request_model=SaveSubmissionSessionAnswerRequest,
    response_model=SubmissionSessionAnswerResponse,
    tags=["Respondent Submission Sessions"],
    auth_required=False,
)
@respondent_bp.route("/submission-sessions/current/answers/<uuid:field_uuid>", methods=["PUT"])
def save_submission_session_answer(field_uuid: SurveyFieldUuid):
    payload = parse(SaveSubmissionSessionAnswerRequest, request)
    if payload.field_uuid != field_uuid:
        raise AnswerSaveError("field_uuid must match the answer URL.")
    core_db = get_core_db()
    response_db = get_response_db()

    result = session_management_service.save_answer(
        core_db,
        response_db,
        raw_resume_token=get_submission_session_token(),
        field_uuid=payload.field_uuid,
        answer=payload,
        client_mutation_id=payload.client_mutation_id,
    )

    response = _SAVED_ANSWER.validate_python(
        payload.model_dump() | {"field_uuid": result.field_uuid, "saved_at": result.saved_at}
    )
    return response.model_dump(mode="json", exclude_none=True), 200


@openapi_route(
    summary="Record submission session event",
    request_model=SubmissionSessionEventRequest,
    status_code=204,
    tags=["Respondent Submission Sessions"],
    auth_required=False,
)
@respondent_bp.route("/submission-sessions/current/events", methods=["POST"])
def record_submission_session_event():
    payload = parse(SubmissionSessionEventRequest, request)
    core_db = get_core_db()
    response_db = get_response_db()

    session_management_service.record_field_viewed(
        core_db,
        response_db,
        raw_resume_token=get_submission_session_token(),
        field_uuid=payload.field_uuid,
    )
    return "", 204


@openapi_route(
    summary="Complete submission session",
    response_model=CompleteSubmissionSessionResponse,
    tags=["Respondent Submission Sessions"],
    auth_required=False,
)
@respondent_bp.route("/submission-sessions/current/complete", methods=["POST"])
def complete_submission_session():
    core_db = get_core_db()
    response_db = get_response_db()

    result = session_management_service.complete_session(
        core_db,
        response_db,
        raw_resume_token=get_submission_session_token(),
    )
    response = CompleteSubmissionSessionResponse(status="completed", completed_at=result.completed_at)
    return response.model_dump(mode="json"), 200


_SAVED_ANSWER = TypeAdapter(SubmissionSessionAnswerResponse)
