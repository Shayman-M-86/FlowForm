from typing import Any

from flask import Blueprint, request
from sqlalchemy.exc import IntegrityError

from app.api.hel import parse
from app.core.responses import ErrorResponse, SuccessResponse, success_response
from app.db.context import get_core_db, get_response_db
from app.db.transaction import commit_or_rollback
from app.schema.api.requests.content import (
    CreateQuestionRequest,
    CreateRuleRequest,
    CreateScoringRuleRequest,
    UpdateQuestionRequest,
    UpdateRuleRequest,
    UpdateScoringRuleRequest,
)
from app.schema.api.requests.public_links import CreatePublicLinkRequest, UpdatePublicLinkRequest
from app.schema.api.requests.submissions import CreateSubmissionRequest
from app.schema.api.requests.surveys import CreateSurveyRequest, UpdateSurveyRequest
from app.schema.api.responses.content import QuestionOut, RuleOut, ScoringRuleOut
from app.schema.api.responses.public_links import PublicLinkCreatedOut, PublicLinkOut
from app.schema.api.responses.submissions import AnswerOut, CoreSubmissionOut, LinkedSubmissionOut
from app.schema.api.responses.surveys import SurveyOut, SurveyVersionOut
from app.schema.orm.core.survey import SurveyVersion
from app.schema.orm.core.survey_submission import SurveySubmission
from app.services import draft_content as content_svc
from app.repository import public_link_repo as link_svc
from app.repositories import surveys_repo as survey_svc
from app.services.submission_gateway import SubmissionGateway

projects_bp = Blueprint("projects_v1", __name__)

_gateway = SubmissionGateway()


# ── Surveys ───────────────────────────────────────────────────────────────────


@projects_bp.route("/<int:project_id>/surveys", methods=["GET"])
def list_surveys(project_id: int):
    db = get_core_db()
    surveys = survey_svc.list_surveys(db, project_id)
    return success_response(data=[SurveyOut.model_validate(s).model_dump(mode="json") for s in surveys])


@projects_bp.route("/<int:project_id>/surveys", methods=["POST"])
def create_survey(project_id: int):
    db = get_core_db()
    data, err = _parse(CreateSurveyRequest, request)
    if err:
        return err.to_response()
    try:
        survey = survey_svc.create_survey(db, project_id, data)
        commit_or_rollback(db)
    except IntegrityError:
        db.rollback()
        return ErrorResponse.return_it("Conflict — check slug uniqueness", "CONFLICT", status_code=409)
    return SuccessResponse.return_it(data=SurveyOut.model_validate(survey).model_dump(mode="json"), status_code=201)


@projects_bp.route("/<int:project_id>/surveys/<int:survey_id>", methods=["GET"])
def get_survey(project_id: int, survey_id: int):
    db = get_core_db()
    survey = survey_svc.get_survey(db, project_id, survey_id)
    if survey is None:
        return ErrorResponse.return_it("Survey not found", "NOT_FOUND", status_code=404)
    return SuccessResponse.return_it(data=SurveyOut.model_validate(survey).model_dump(mode="json"))


@projects_bp.route("/<int:project_id>/surveys/<int:survey_id>", methods=["PATCH"])
def update_survey(project_id: int, survey_id: int):
    db = get_core_db()
    survey = survey_svc.get_survey(db, project_id, survey_id)
    if survey is None:
        return ErrorResponse.return_it("Survey not found", "NOT_FOUND", status_code=404)
    data, err = _parse(UpdateSurveyRequest, request)
    if err:
        return err.to_response()
    try:
        survey = survey_svc.update_survey(db, survey, data)
        commit_or_rollback(db)
    except IntegrityError:
        db.rollback()
        return ErrorResponse.return_it("Conflict — check slug uniqueness", "CONFLICT", status_code=409)
    return SuccessResponse.return_it(data=SurveyOut.model_validate(survey).model_dump(mode="json"))


@projects_bp.route("/<int:project_id>/surveys/<int:survey_id>", methods=["DELETE"])
def delete_survey(project_id: int, survey_id: int):
    db = get_core_db()
    survey = survey_svc.get_survey(db, project_id, survey_id)
    if survey is None:
        return ErrorResponse.return_it("Survey not found", "NOT_FOUND", status_code=404)
    survey_svc.delete_survey(db, survey)
    commit_or_rollback(db)
    return SuccessResponse.return_it(message="Survey deleted")


# ── Survey versions ───────────────────────────────────────────────────────────


@projects_bp.route("/<int:project_id>/surveys/<int:survey_id>/versions", methods=["GET"])
def list_versions(project_id: int, survey_id: int):
    db = get_core_db()
    if survey_svc.get_survey(db, project_id, survey_id) is None:
        return ErrorResponse.return_it("Survey not found", "NOT_FOUND", status_code=404)
    versions = survey_svc.list_versions(db, survey_id)
    return SuccessResponse.return_it(
        data=[SurveyVersionOut.model_validate(v).model_dump(mode="json") for v in versions]
    )


@projects_bp.route("/<int:project_id>/surveys/<int:survey_id>/versions", methods=["POST"])
def create_version(project_id: int, survey_id: int):
    db = get_core_db()
    if survey_svc.get_survey(db, project_id, survey_id) is None:
        return ErrorResponse.return_it("Survey not found", "NOT_FOUND", status_code=404)
    version = survey_svc.create_version(db, survey_id)
    commit_or_rollback(db)
    return SuccessResponse.return_it(
        data=SurveyVersionOut.model_validate(version).model_dump(mode="json"), status_code=201
    )


@projects_bp.route("/<int:project_id>/surveys/<int:survey_id>/versions/<int:version_id>", methods=["GET"])
def get_version(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    if survey_svc.get_survey(db, project_id, survey_id) is None:
        return ErrorResponse.return_it("Survey not found", "NOT_FOUND", status_code=404)
    version = survey_svc.get_version(db, survey_id, version_id)
    if version is None:
        return ErrorResponse.return_it("Version not found", "NOT_FOUND", status_code=404)
    return SuccessResponse.return_it(data=SurveyVersionOut.model_validate(version).model_dump(mode="json"))


@projects_bp.route(
    "/<int:project_id>/surveys/<int:survey_id>/versions/<int:version_id>/publish",
    methods=["POST"],
)
def publish_version(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    survey = survey_svc.get_survey(db, project_id, survey_id)
    if survey is None:
        return ErrorResponse.return_it("Survey not found", "NOT_FOUND", status_code=404)
    version = survey_svc.get_version(db, survey_id, version_id)
    if version is None:
        return ErrorResponse.return_it("Version not found", "NOT_FOUND", status_code=404)
    try:
        version = survey_svc.publish_version(db, survey, version)
        commit_or_rollback(db)
    except ValueError as exc:
        return ErrorResponse.return_it(str(exc), "INVALID_REQUEST", status_code=400)
    return SuccessResponse.return_it(data=SurveyVersionOut.model_validate(version).model_dump(mode="json"))


@projects_bp.route(
    "/<int:project_id>/surveys/<int:survey_id>/versions/<int:version_id>/archive",
    methods=["POST"],
)
def archive_version(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    if survey_svc.get_survey(db, project_id, survey_id) is None:
        return ErrorResponse.return_it("Survey not found", "NOT_FOUND", status_code=404)
    version = survey_svc.get_version(db, survey_id, version_id)
    if version is None:
        return ErrorResponse.return_it("Version not found", "NOT_FOUND", status_code=404)
    try:
        version = survey_svc.archive_version(db, version)
        commit_or_rollback(db)
    except ValueError as exc:
        return ErrorResponse.return_it(str(exc), "INVALID_REQUEST", status_code=400)
    return SuccessResponse.return_it(data=SurveyVersionOut.model_validate(version).model_dump(mode="json"))


# ── Questions ─────────────────────────────────────────────────────────────────


def _get_version_or_404(
    db, project_id, survey_id, version_id
) -> tuple[SurveyVersion, None] | tuple[Any, ErrorResponse]:
    if survey_svc.get_survey(db, project_id, survey_id) is None:
        return None, ErrorResponse("Survey not found", "NOT_FOUND", status_code=404)
    version = survey_svc.get_version(db, survey_id, version_id)
    if version is None:
        return None, ErrorResponse("Version not found", "NOT_FOUND", status_code=404)
    return version, None


_QBASE = "/<int:project_id>/surveys/<int:survey_id>/versions/<int:version_id>/questions"


@projects_bp.route(_QBASE, methods=["GET"])
def list_questions(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    version, err = _get_version_or_404(db, project_id, survey_id, version_id)
    if err:
        return err.to_response()
    questions = content_svc.list_questions(db, version.id)
    return success_response(data=[QuestionOut.model_validate(q).model_dump(mode="json") for q in questions])


@projects_bp.route(_QBASE, methods=["POST"])
def create_question(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    version, err = _get_version_or_404(db, project_id, survey_id, version_id)
    if err:
        return err.to_response()
    data, err = _parse(CreateQuestionRequest, request)
    if err:
        return err.to_response()
    try:
        question = content_svc.create_question(db, version, data)
        commit_or_rollback(db)
    except ValueError as exc:
        return ErrorResponse.return_it(str(exc), "INVALID_REQUEST", status_code=400)
    except IntegrityError:
        db.rollback()
        return ErrorResponse.return_it("Duplicate question_key in this version", "CONFLICT", status_code=409)
    return SuccessResponse.return_it(data=QuestionOut.model_validate(question).model_dump(mode="json"), status_code=201)


@projects_bp.route(f"{_QBASE}/<int:question_id>", methods=["PATCH"])
def update_question(project_id: int, survey_id: int, version_id: int, question_id: int):
    db = get_core_db()
    version, err = _get_version_or_404(db, project_id, survey_id, version_id)
    if err:
        return err.to_response()
    question = content_svc.get_question(db, version_id, question_id)
    if question is None:
        return ErrorResponse.return_it("Question not found", "NOT_FOUND", status_code=404)
    data, err = _parse(UpdateQuestionRequest, request)
    if err:
        return err.to_response()
    try:
        question = content_svc.update_question(db, version, question, data)
        commit_or_rollback(db)
    except ValueError as exc:
        return ErrorResponse.return_it(str(exc), "INVALID_REQUEST", status_code=400)
    except IntegrityError:
        db.rollback()
        return ErrorResponse.return_it("Duplicate question_key in this version", "CONFLICT", status_code=409)
    return SuccessResponse.return_it(data=QuestionOut.model_validate(question).model_dump(mode="json"))


@projects_bp.route(f"{_QBASE}/<int:question_id>", methods=["DELETE"])
def delete_question(project_id: int, survey_id: int, version_id: int, question_id: int):
    db = get_core_db()
    version, err = _get_version_or_404(db, project_id, survey_id, version_id)
    if err:
        return err.to_response()
    question = content_svc.get_question(db, version_id, question_id)
    if question is None:
        return ErrorResponse.return_it("Question not found", "NOT_FOUND", status_code=404)
    try:
        content_svc.delete_question(db, version, question)
        commit_or_rollback(db)
    except ValueError as exc:
        return ErrorResponse.return_it(str(exc), "INVALID_REQUEST", status_code=400)
    return SuccessResponse.return_it(message="Question deleted")


# ── Rules ─────────────────────────────────────────────────────────────────────

_RBASE = "/<int:project_id>/surveys/<int:survey_id>/versions/<int:version_id>/rules"


@projects_bp.route(_RBASE, methods=["GET"])
def list_rules(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    version, err = _get_version_or_404(db, project_id, survey_id, version_id)
    if err:
        return err.to_response()
    rules = content_svc.list_rules(db, version.id)
    return SuccessResponse.return_it(data=[RuleOut.model_validate(r).model_dump(mode="json") for r in rules])


@projects_bp.route(_RBASE, methods=["POST"])
def create_rule(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    version, err = _get_version_or_404(db, project_id, survey_id, version_id)
    if err:
        return err.to_response()
    data, err = _parse(CreateRuleRequest, request)
    if err:
        return err.to_response()
    try:
        rule = content_svc.create_rule(db, version, data)
        commit_or_rollback(db)
    except ValueError as exc:
        return ErrorResponse.return_it(str(exc), "INVALID_REQUEST", status_code=400)
    except IntegrityError:
        db.rollback()
        return ErrorResponse.return_it("Duplicate rule_key in this version", "CONFLICT", status_code=409)
    return SuccessResponse.return_it(data=RuleOut.model_validate(rule).model_dump(mode="json"), status_code=201)


@projects_bp.route(f"{_RBASE}/<int:rule_id>", methods=["PATCH"])
def update_rule(project_id: int, survey_id: int, version_id: int, rule_id: int):
    db = get_core_db()
    version, err = _get_version_or_404(db, project_id, survey_id, version_id)
    if err:
        return err.to_response()
    rule = content_svc.get_rule(db, version_id, rule_id)
    if rule is None:
        return ErrorResponse.return_it("Rule not found", "NOT_FOUND", status_code=404)
    data, err = _parse(UpdateRuleRequest, request)
    if err:
        return err.to_response()
    try:
        rule = content_svc.update_rule(db, version, rule, data)
        commit_or_rollback(db)
    except ValueError as exc:
        return ErrorResponse.return_it(str(exc), "INVALID_REQUEST", status_code=400)
    except IntegrityError:
        db.rollback()
        return ErrorResponse.return_it("Duplicate rule_key in this version", "CONFLICT", status_code=409)
    return SuccessResponse.return_it(data=RuleOut.model_validate(rule).model_dump(mode="json"))


@projects_bp.route(f"{_RBASE}/<int:rule_id>", methods=["DELETE"])
def delete_rule(project_id: int, survey_id: int, version_id: int, rule_id: int):
    db = get_core_db()
    version, err = _get_version_or_404(db, project_id, survey_id, version_id)
    if err:
        return err.to_response()
    rule = content_svc.get_rule(db, version_id, rule_id)
    if rule is None:
        return ErrorResponse.return_it("Rule not found", "NOT_FOUND", status_code=404)
    try:
        content_svc.delete_rule(db, version, rule)
        commit_or_rollback(db)
    except ValueError as exc:
        return ErrorResponse.return_it(str(exc), "INVALID_REQUEST", status_code=400)
    return SuccessResponse.return_it(message="Rule deleted")


# ── Scoring rules ─────────────────────────────────────────────────────────────

_SBASE = "/<int:project_id>/surveys/<int:survey_id>/versions/<int:version_id>/scoring-rules"


@projects_bp.route(_SBASE, methods=["GET"])
def list_scoring_rules(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    version, err = _get_version_or_404(db, project_id, survey_id, version_id)
    if err:
        return err.to_response()
    rules = content_svc.list_scoring_rules(db, version.id)
    return SuccessResponse.return_it(data=[ScoringRuleOut.model_validate(r).model_dump(mode="json") for r in rules])


@projects_bp.route(_SBASE, methods=["POST"])
def create_scoring_rule(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    version, err = _get_version_or_404(db, project_id, survey_id, version_id)
    if err:
        return err.to_response()
    data, err = _parse(CreateScoringRuleRequest, request)
    if err:
        return err.to_response()
    try:
        rule = content_svc.create_scoring_rule(db, version, data)
        commit_or_rollback(db)
    except ValueError as exc:
        return ErrorResponse.return_it(str(exc), "INVALID_REQUEST", status_code=400)
    except IntegrityError:
        db.rollback()
        return ErrorResponse.return_it("Duplicate scoring_key in this version", "CONFLICT", status_code=409)
    return SuccessResponse.return_it(data=ScoringRuleOut.model_validate(rule).model_dump(mode="json"), status_code=201)


@projects_bp.route(f"{_SBASE}/<int:scoring_rule_id>", methods=["PATCH"])
def update_scoring_rule(project_id: int, survey_id: int, version_id: int, scoring_rule_id: int):
    db = get_core_db()
    version, err = _get_version_or_404(db, project_id, survey_id, version_id)
    if err:
        return err.to_response()
    rule = content_svc.get_scoring_rule(db, version_id, scoring_rule_id)
    if rule is None:
        return ErrorResponse.return_it("Scoring rule not found", "NOT_FOUND", status_code=404)
    data, err = _parse(UpdateScoringRuleRequest, request)
    if err:
        return err.to_response()
    try:
        rule = content_svc.update_scoring_rule(db, version, rule, data)
        commit_or_rollback(db)
    except ValueError as exc:
        return ErrorResponse.return_it(str(exc), "INVALID_REQUEST", status_code=400)
    except IntegrityError:
        db.rollback()
        return ErrorResponse.return_it("Duplicate scoring_key in this version", "CONFLICT", status_code=409)
    return SuccessResponse.return_it(data=ScoringRuleOut.model_validate(rule).model_dump(mode="json"))


@projects_bp.route(f"{_SBASE}/<int:scoring_rule_id>", methods=["DELETE"])
def delete_scoring_rule(project_id: int, survey_id: int, version_id: int, scoring_rule_id: int):
    db = get_core_db()
    version, err = _get_version_or_404(db, project_id, survey_id, version_id)
    if err:
        return err.to_response()
    rule = content_svc.get_scoring_rule(db, version_id, scoring_rule_id)
    if rule is None:
        return ErrorResponse.return_it("Scoring rule not found", "NOT_FOUND", status_code=404)
    try:
        content_svc.delete_scoring_rule(db, version, rule)
        commit_or_rollback(db)
    except ValueError as exc:
        return ErrorResponse.return_it(str(exc), "INVALID_REQUEST", status_code=400)
    return SuccessResponse.return_it(message="Scoring rule deleted")


# ── Public links ──────────────────────────────────────────────────────────────

_LBASE = "/<int:project_id>/surveys/<int:survey_id>/public-links"


@projects_bp.route(_LBASE, methods=["GET"])
def list_public_links(project_id: int, survey_id: int):
    db = get_core_db()
    if survey_svc.get_survey(db, project_id, survey_id) is None:
        return ErrorResponse.return_it("Survey not found", "NOT_FOUND", status_code=404)
    links = link_svc.list_links(db, survey_id)
    return SuccessResponse.return_it(
        data=[PublicLinkOut.model_validate(link).model_dump(mode="json") for link in links]
    )


@projects_bp.route(_LBASE, methods=["POST"])
def create_public_link(project_id: int, survey_id: int):
    db = get_core_db()
    if survey_svc.get_survey(db, project_id, survey_id) is None:
        return ErrorResponse.return_it("Survey not found", "NOT_FOUND", status_code=404)
    data, err = _parse(CreatePublicLinkRequest, request)
    if err:
        return err.to_response()
    link, token = link_svc.create_link(db, survey_id, data)
    commit_or_rollback(db)
    return SuccessResponse.return_it(
        data=PublicLinkCreatedOut(
            id=link.id,
            survey_id=link.survey_id,
            token=token,
            token_prefix=link.token_prefix,
            is_active=link.is_active,
            allow_response=link.allow_response,
            expires_at=link.expires_at,
            created_at=link.created_at,
        ).model_dump(mode="json"),
        status_code=201,
    )


@projects_bp.route(f"{_LBASE}/<int:link_id>", methods=["PATCH"])
def update_public_link(project_id: int, survey_id: int, link_id: int):
    db = get_core_db()
    if survey_svc.get_survey(db, project_id, survey_id) is None:
        return ErrorResponse.return_it("Survey not found", "NOT_FOUND", status_code=404)
    link = link_svc.get_link(db, survey_id, link_id)
    if link is None:
        return ErrorResponse.return_it("Public link not found", "NOT_FOUND", status_code=404)
    data, err = _parse(UpdatePublicLinkRequest, request)
    if err:
        return err.to_response()
    link = link_svc.update_link(db, link, data)
    commit_or_rollback(db)
    return SuccessResponse.return_it(data=PublicLinkOut.model_validate(link).model_dump(mode="json"))


@projects_bp.route(f"{_LBASE}/<int:link_id>", methods=["DELETE"])
def delete_public_link(project_id: int, survey_id: int, link_id: int):
    db = get_core_db()
    if survey_svc.get_survey(db, project_id, survey_id) is None:
        return ErrorResponse.return_it("Survey not found", "NOT_FOUND", status_code=404)
    link = link_svc.get_link(db, survey_id, link_id)
    if link is None:
        return ErrorResponse.return_it("Public link not found", "NOT_FOUND", status_code=404)
    link_svc.delete_link(db, link)
    commit_or_rollback(db)
    return SuccessResponse.return_it(message="Public link deleted")


# ── Submissions (authenticated) ───────────────────────────────────────────────


@projects_bp.route("/<int:project_id>/surveys/<int:survey_id>/submissions", methods=["POST"])
def create_submission(project_id: int, survey_id: int):
    core_db = get_core_db()
    response_db = get_response_db()

    survey = survey_svc.get_survey(core_db, project_id, survey_id)
    if survey is None:
        return ErrorResponse.return_it("Survey not found", "NOT_FOUND", status_code=404)
    if survey.published_version_id is None:
        return ErrorResponse.return_it("Survey has no published version", "INVALID_REQUEST", status_code=400)

    data, err = _parse(CreateSubmissionRequest, request)
    if err:
        return err.to_response()

    # Determine response_store_id from the survey
    if survey.default_response_store_id is None:
        return ErrorResponse.return_it(
            "Survey has no default response store configured", "INVALID_REQUEST", status_code=400
        )

    pseudonymous_subject_id = None
    if data.submitted_by_user_id is not None and not data.is_anonymous:
        mapping = _gateway.get_or_create_subject_mapping(
            core_db, project_id=project_id, user_id=data.submitted_by_user_id
        )
        pseudonymous_subject_id = mapping.pseudonymous_subject_id

    try:
        linked = _gateway.create_linked_submission(
            core_db,
            response_db,
            project_id=project_id,
            survey_id=survey_id,
            survey_version_id=data.survey_version_id,
            response_store_id=survey.default_response_store_id,
            submission_channel="authenticated" if data.submitted_by_user_id else "system",
            submitted_by_user_id=data.submitted_by_user_id,
            pseudonymous_subject_id=pseudonymous_subject_id,
            is_anonymous=data.is_anonymous,
            started_at=data.started_at,
            submitted_at=data.submitted_at,
            answers=[a.model_dump() for a in data.answers],
            metadata=data.metadata,
        )
    except Exception as exc:
        return ErrorResponse.return_it(str(exc.args), "SUBMISSION_FAILED", status_code=500)

    return SuccessResponse.return_it(
        data=LinkedSubmissionOut(
            core=CoreSubmissionOut.model_validate(linked.core_submission),
            answers=[AnswerOut.model_validate(a) for a in linked.answers],
        ).model_dump(mode="json"),
        status_code=201,
    )


@projects_bp.route("/<int:project_id>/submissions", methods=["GET"])
def list_submissions(project_id: int):
    from sqlalchemy import select

    db = get_core_db()
    query = select(SurveySubmission).where(SurveySubmission.project_id == project_id)

    survey_id = request.args.get("survey_id", type=int)
    status = request.args.get("status")
    channel = request.args.get("submission_channel")

    if survey_id is not None:
        query = query.where(SurveySubmission.survey_id == survey_id)
    if status:
        query = query.where(SurveySubmission.status == status)
    if channel:
        query = query.where(SurveySubmission.submission_channel == channel)

    submissions = list(db.scalars(query))
    return SuccessResponse.return_it(
        data=[CoreSubmissionOut.model_validate(s).model_dump(mode="json") for s in submissions]
    )


@projects_bp.route("/<int:project_id>/submissions/<int:submission_id>", methods=["GET"])
def get_submission(project_id: int, submission_id: int):
    core_db = get_core_db()
    response_db = get_response_db()

    include_answers = request.args.get("include_answers", "false").lower() == "true"
    resolve_identity = request.args.get("resolve_identity", "false").lower() == "true"

    linked = _gateway.load_linked_submission(
        core_db,
        response_db,
        core_submission_id=submission_id,
        include_answers=include_answers,
        resolve_identity=resolve_identity,
    )
    if linked is None or linked.core_submission.project_id != project_id:
        return ErrorResponse.return_it("Submission not found", "NOT_FOUND", status_code=404)

    return SuccessResponse.return_it(
        data=LinkedSubmissionOut(
            core=CoreSubmissionOut.model_validate(linked.core_submission),
            answers=[AnswerOut.model_validate(a) for a in linked.answers],
        ).model_dump(mode="json")
    )
