from logging import getLogger

from flask import Blueprint, request, url_for

from app.api.utils.validation import parse, parse_query
from app.db.context import get_core_db, get_response_db
from app.repositories import surveys_repo as survey_svc
from app.schema.api.requests.content import (
    CreateQuestionRequest,
    CreateRuleRequest,
    CreateScoringRuleRequest,
    UpdateQuestionRequest,
    UpdateRuleRequest,
    UpdateScoringRuleRequest,
)
from app.schema.api.requests.public_links import CreatePublicLinkRequest, UpdatePublicLinkRequest
from app.schema.api.requests.submissions import CreateSubmissionRequest, GetSubmissionRequest, ListSubmissionsRequest
from app.schema.api.requests.surveys import CreateSurveyRequest, UpdateSurveyRequest
from app.schema.api.responses.content import QuestionOut, RuleOut, ScoringRuleOut
from app.schema.api.responses.public_links import CreatePublicLinkOut, ListPublicLinksOut, PublicLinkOut
from app.schema.api.responses.submissions import (
    AnswerOut,
    CoreSubmissionOut,
    LinkedSubmissionOut,
    PaginatedSubmissionsOut,
)
from app.schema.api.responses.surveys import SurveyOut, SurveyVersionOut
from app.services.content import ContentService
from app.services.public_links import PublicLinkService
from app.services.submissions import SubmissionService
from app.services.surveys import SurveyService
from app.core.extensions import auth
logger = getLogger(__name__)

projects_bp = Blueprint("projects_v1", __name__)

content_svc = ContentService()
public_link_svc = PublicLinkService()
survey_service = SurveyService()
submission_service = SubmissionService()


# ── Surveys ───────────────────────────────────────────────────────────────────


@projects_bp.route("/<int:project_id>/surveys", methods=["GET"])
@auth.require_auth()
def list_surveys(project_id: int):
    db = get_core_db()
    surveys = survey_svc.list_surveys(db, project_id)
    return [SurveyOut.model_validate(s).model_dump(mode="json") for s in surveys], 200


@projects_bp.route("/<int:project_id>/surveys", methods=["POST"])
@auth.require_auth()
def create_survey(project_id: int):
    payload = parse(CreateSurveyRequest, request)
    db = get_core_db()
    survey = survey_service.create_survey(db, project_id, payload)
    return SurveyOut.model_validate(survey).model_dump(mode="json"), 201


@projects_bp.route("/<int:project_id>/surveys/<int:survey_id>", methods=["GET"])
@auth.require_auth()
def get_survey(project_id: int, survey_id: int):
    db = get_core_db()
    survey = survey_service.get_survey(db, project_id, survey_id)
    return SurveyOut.model_validate(survey).model_dump(mode="json"), 200


@projects_bp.route("/<int:project_id>/surveys/<int:survey_id>", methods=["PATCH"])
@auth.require_auth()
def update_survey(project_id: int, survey_id: int):
    payload = parse(UpdateSurveyRequest, request)
    db = get_core_db()
    survey = survey_service.update_survey(db, project_id, survey_id, payload)
    return SurveyOut.model_validate(survey).model_dump(mode="json"), 200


@projects_bp.route("/<int:project_id>/surveys/<int:survey_id>", methods=["DELETE"])
def delete_survey(project_id: int, survey_id: int):
    db = get_core_db()
    survey_service.delete_survey(db, project_id, survey_id)
    return {"message": "Survey deleted"}, 200


# ── Survey versions ───────────────────────────────────────────────────────────


@projects_bp.route("/<int:project_id>/surveys/<int:survey_id>/versions", methods=["GET"])
def list_versions(project_id: int, survey_id: int):
    db = get_core_db()
    versions = survey_service.list_versions(db, project_id, survey_id)
    return [SurveyVersionOut.model_validate(v).model_dump(mode="json") for v in versions], 200


@projects_bp.route("/<int:project_id>/surveys/<int:survey_id>/versions", methods=["POST"])
def create_version(project_id: int, survey_id: int):
    db = get_core_db()
    version = survey_service.create_version(db, project_id, survey_id)
    return SurveyVersionOut.model_validate(version).model_dump(mode="json"), 201


@projects_bp.route("/<int:project_id>/surveys/<int:survey_id>/versions/<int:version_id>", methods=["GET"])
def get_version(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    version = survey_service.get_version(db, project_id, survey_id, version_id)
    return SurveyVersionOut.model_validate(version).model_dump(mode="json"), 200


@projects_bp.route(
    "/<int:project_id>/surveys/<int:survey_id>/versions/<int:version_id>/publish",
    methods=["POST"],
)
def publish_version(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    version = survey_service.publish_version(db, project_id, survey_id, version_id)
    return SurveyVersionOut.model_validate(version).model_dump(mode="json"), 200


@projects_bp.route(
    "/<int:project_id>/surveys/<int:survey_id>/versions/<int:version_id>/archive",
    methods=["POST"],
)
def archive_version(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    version = survey_service.archive_version(db, project_id, survey_id, version_id)
    return SurveyVersionOut.model_validate(version).model_dump(mode="json"), 200


# ── Questions ─────────────────────────────────────────────────────────────────

_QBASE = "/<int:project_id>/surveys/<int:survey_id>/versions/<int:version_id>/questions"


@projects_bp.route(_QBASE, methods=["GET"])
def list_questions(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    questions = content_svc.list_questions(db, project_id, survey_id, version_id)
    return [QuestionOut.model_validate(q).model_dump(mode="json") for q in questions], 200


@projects_bp.route(_QBASE, methods=["POST"])
def create_question(project_id: int, survey_id: int, version_id: int):
    payload = parse(CreateQuestionRequest, request)
    db = get_core_db()
    question = content_svc.create_question(db, project_id, survey_id, version_id, payload)
    return QuestionOut.model_validate(question).model_dump(mode="json"), 201


@projects_bp.route(f"{_QBASE}/<int:question_id>", methods=["PATCH"])
def update_question(project_id: int, survey_id: int, version_id: int, question_id: int):
    payload = parse(UpdateQuestionRequest, request)
    db = get_core_db()
    question = content_svc.update_question(db, project_id, survey_id, version_id, question_id, payload)
    return QuestionOut.model_validate(question).model_dump(mode="json"), 200


@projects_bp.route(f"{_QBASE}/<int:question_id>", methods=["DELETE"])
def delete_question(project_id: int, survey_id: int, version_id: int, question_id: int):
    db = get_core_db()
    content_svc.delete_question(db, project_id, survey_id, version_id, question_id)
    return {"message": "Question deleted"}, 200


# ── Rules ─────────────────────────────────────────────────────────────────────

_RBASE = "/<int:project_id>/surveys/<int:survey_id>/versions/<int:version_id>/rules"


@projects_bp.route(_RBASE, methods=["GET"])
def list_rules(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    rules = content_svc.list_rules(db, project_id, survey_id, version_id)
    return [RuleOut.model_validate(r).model_dump(mode="json") for r in rules], 200


@projects_bp.route(_RBASE, methods=["POST"])
def create_rule(project_id: int, survey_id: int, version_id: int):
    payload = parse(CreateRuleRequest, request)
    db = get_core_db()
    rule = content_svc.create_rule(db, project_id, survey_id, version_id, payload)
    return RuleOut.model_validate(rule).model_dump(mode="json"), 201


@projects_bp.route(f"{_RBASE}/<int:rule_id>", methods=["PATCH"])
def update_rule(project_id: int, survey_id: int, version_id: int, rule_id: int):
    payload = parse(UpdateRuleRequest, request)
    db = get_core_db()
    rule = content_svc.update_rule(db, project_id, survey_id, version_id, rule_id, payload)
    return RuleOut.model_validate(rule).model_dump(mode="json"), 200


@projects_bp.route(f"{_RBASE}/<int:rule_id>", methods=["DELETE"])
def delete_rule(project_id: int, survey_id: int, version_id: int, rule_id: int):
    db = get_core_db()
    content_svc.delete_rule(db, project_id, survey_id, version_id, rule_id)
    return {"message": "Rule deleted"}, 200


# ── Scoring rules ─────────────────────────────────────────────────────────────

_SBASE = "/<int:project_id>/surveys/<int:survey_id>/versions/<int:version_id>/scoring-rules"


@projects_bp.route(_SBASE, methods=["GET"])
def list_scoring_rules(project_id: int, survey_id: int, version_id: int):
    db = get_core_db()
    rules = content_svc.list_scoring_rules(db, project_id, survey_id, version_id)
    return [ScoringRuleOut.model_validate(r).model_dump(mode="json") for r in rules], 200


@projects_bp.route(_SBASE, methods=["POST"])
def create_scoring_rule(project_id: int, survey_id: int, version_id: int):
    payload = parse(CreateScoringRuleRequest, request)
    db = get_core_db()
    rule = content_svc.create_scoring_rule(db, project_id, survey_id, version_id, payload)
    return ScoringRuleOut.model_validate(rule).model_dump(mode="json"), 201


@projects_bp.route(f"{_SBASE}/<int:scoring_rule_id>", methods=["PATCH"])
def update_scoring_rule(project_id: int, survey_id: int, version_id: int, scoring_rule_id: int):
    payload = parse(UpdateScoringRuleRequest, request)
    db = get_core_db()
    rule = content_svc.update_scoring_rule(db, project_id, survey_id, version_id, scoring_rule_id, payload)
    return ScoringRuleOut.model_validate(rule).model_dump(mode="json"), 200


@projects_bp.route(f"{_SBASE}/<int:scoring_rule_id>", methods=["DELETE"])
def delete_scoring_rule(project_id: int, survey_id: int, version_id: int, scoring_rule_id: int):
    db = get_core_db()
    content_svc.delete_scoring_rule(db, project_id, survey_id, version_id, scoring_rule_id)
    return {"message": "Scoring rule deleted"}, 200


# ── Public links ──────────────────────────────────────────────────────────────

_LBASE = "/<int:project_id>/surveys/<int:survey_id>/public-links"


@projects_bp.route(_LBASE, methods=["GET"])
def list_public_links(project_id: int, survey_id: int):
    db = get_core_db()
    links = public_link_svc.list_links(db, project_id, survey_id)
    return ListPublicLinksOut(links=[PublicLinkOut.model_validate(link) for link in links]).model_dump(mode="json"), 200


@projects_bp.route(_LBASE, methods=["POST"])
def create_public_link(project_id: int, survey_id: int):
    payload = parse(CreatePublicLinkRequest, request)
    db = get_core_db()

    result = public_link_svc.create_link(
        db,
        survey_id=survey_id,
        project_id=project_id,
        data=payload,
    )
    public_url = url_for(
        "public_v1.resolve_link",  # use your real endpoint name here
        token=result.token,
        _external=True,
    )
    response = CreatePublicLinkOut(
        link=PublicLinkOut.model_validate(result.link),
        token=result.token,
        url=public_url,
    )
    return response.model_dump(mode="json"), 201


@projects_bp.route(f"{_LBASE}/<int:link_id>", methods=["PATCH"])
def update_public_link(project_id: int, survey_id: int, link_id: int):
    payload = parse(UpdatePublicLinkRequest, request)
    db = get_core_db()
    updated_link = public_link_svc.update_link(
        db,
        survey_id=survey_id,
        project_id=project_id,
        link_id=link_id,
        payload=payload,
    )
    return PublicLinkOut.model_validate(updated_link).model_dump(mode="json"), 200


@projects_bp.route(f"{_LBASE}/<int:link_id>", methods=["DELETE"])
def delete_public_link(project_id: int, survey_id: int, link_id: int):
    db = get_core_db()
    public_link_svc.delete_link(db, survey_id=survey_id, project_id=project_id, link_id=link_id)
    return {"message": "Public link deleted"}, 200


# ── Submissions (authenticated) ───────────────────────────────────────────────


@projects_bp.route("/<int:project_id>/surveys/<int:survey_id>/submissions", methods=["POST"])
def create_submission(project_id: int, survey_id: int):
    payload = parse(CreateSubmissionRequest, request)
    core_db = get_core_db()
    response_db = get_response_db()
    linked = submission_service.create_project_submission(
        core_db,
        response_db,
        project_id=project_id,
        survey_id=survey_id,
        payload=payload,
    )

    response = LinkedSubmissionOut(
        core=CoreSubmissionOut.model_validate(linked.core_submission),
        answers=[AnswerOut.model_validate(a) for a in linked.answers],
    )

    return response.model_dump(mode="json"), 201


@projects_bp.route("/<int:project_id>/submissions", methods=["GET"])
def list_submissions(project_id: int):
    payload = parse_query(ListSubmissionsRequest, request)

    core_db = get_core_db()

    items, total = submission_service.list_submissions(
        core_db,
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


@projects_bp.route("/<int:project_id>/submissions/<int:submission_id>", methods=["GET"])
def get_submission(project_id: int, submission_id: int):
    payload = parse_query(GetSubmissionRequest, request)

    core_db = get_core_db()
    response_db = get_response_db()

    linked = submission_service.get_submission(
        core_db,
        response_db,
        project_id=project_id,
        submission_id=submission_id,
        params=payload,
    )

    response = LinkedSubmissionOut(
        core=CoreSubmissionOut.model_validate(linked.core_submission),
        answers=[AnswerOut.model_validate(a) for a in linked.answers],
    )

    return response.model_dump(mode="json"), 200
