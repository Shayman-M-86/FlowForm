from flask import request

from app.api.utils.validation import parse
from app.api.v1.projects import content_svc, projects_bp, users_service
from app.api.v1.projects.resolver import resolve_project_ref
from app.core.extensions import auth
from app.db.context import get_core_db
from app.schema.api.requests.content import (
    CreateQuestionRequest,
    CreateRuleRequest,
    CreateScoringRuleRequest,
    UpdateQuestionRequest,
    UpdateRuleRequest,
    UpdateScoringRuleRequest,
)
from app.schema.api.responses.content import QuestionOut, RuleOut, ScoringRuleOut
from app.schema.orm.core.user import User

_QBASE = "/<project_ref>/surveys/<int:survey_id>/versions/<int:version_number>/questions"
_RBASE = "/<project_ref>/surveys/<int:survey_id>/versions/<int:version_number>/rules"
_SBASE = "/<project_ref>/surveys/<int:survey_id>/versions/<int:version_number>/scoring-rules"


# ── Questions ─────────────────────────────────────────────────────────────────


@projects_bp.route(_QBASE, methods=["GET"])
@auth.require_auth()
def list_questions(project_ref: str, survey_id: int, version_number: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    questions = content_svc.list_questions(
        db=db, project_id=project_id, survey_id=survey_id, version_number=version_number, actor=user
    )
    return [QuestionOut.model_validate(q).model_dump(mode="json") for q in questions], 200


@projects_bp.route(_QBASE, methods=["POST"])
@auth.require_auth()
def create_question(project_ref: str, survey_id: int, version_number: int):
    payload = parse(CreateQuestionRequest, request)
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    question = content_svc.create_question(
        db=db, project_id=project_id, survey_id=survey_id, version_number=version_number, data=payload, actor=user
    )
    return QuestionOut.model_validate(question).model_dump(mode="json"), 201


@projects_bp.route(f"{_QBASE}/<int:question_id>", methods=["PATCH"])
@auth.require_auth()
def update_question(project_ref: str, survey_id: int, version_number: int, question_id: int):
    payload = parse(UpdateQuestionRequest, request)
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    question = content_svc.update_question(
        db=db,
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        question_id=question_id,
        data=payload,
        actor=user,
    )
    return QuestionOut.model_validate(question).model_dump(mode="json"), 200


@projects_bp.route(f"{_QBASE}/<int:question_id>", methods=["DELETE"])
@auth.require_auth()
def delete_question(project_ref: str, survey_id: int, version_number: int, question_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    content_svc.delete_question(
        db=db,
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        question_id=question_id,
        actor=user,
    )
    return {"message": "Question deleted"}, 200


# ── Rules ─────────────────────────────────────────────────────────────────────


@projects_bp.route(_RBASE, methods=["GET"])
@auth.require_auth()
def list_rules(project_ref: str, survey_id: int, version_number: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    rules = content_svc.list_rules(
        db=db, project_id=project_id, survey_id=survey_id, version_number=version_number, actor=user
    )
    return [RuleOut.model_validate(r).model_dump(mode="json") for r in rules], 200


@projects_bp.route(_RBASE, methods=["POST"])
@auth.require_auth()
def create_rule(project_ref: str, survey_id: int, version_number: int):
    payload = parse(CreateRuleRequest, request)
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    rule = content_svc.create_rule(
        db=db, project_id=project_id, survey_id=survey_id, version_number=version_number, data=payload, actor=user
    )
    return RuleOut.model_validate(rule).model_dump(mode="json"), 201


@projects_bp.route(f"{_RBASE}/<int:rule_id>", methods=["PATCH"])
@auth.require_auth()
def update_rule(project_ref: str, survey_id: int, version_number: int, rule_id: int):
    payload = parse(UpdateRuleRequest, request)
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    rule = content_svc.update_rule(
        db=db,
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        rule_id=rule_id,
        data=payload,
        actor=user,
    )
    return RuleOut.model_validate(rule).model_dump(mode="json"), 200


@projects_bp.route(f"{_RBASE}/<int:rule_id>", methods=["DELETE"])
@auth.require_auth()
def delete_rule(project_ref: str, survey_id: int, version_number: int, rule_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    content_svc.delete_rule(
        db=db,
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        rule_id=rule_id,
        actor=user,
    )
    return {"message": "Rule deleted"}, 200


# ── Scoring rules ─────────────────────────────────────────────────────────────


@projects_bp.route(_SBASE, methods=["GET"])
@auth.require_auth()
def list_scoring_rules(project_ref: str, survey_id: int, version_number: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    rules = content_svc.list_scoring_rules(
        db=db, project_id=project_id, survey_id=survey_id, version_number=version_number, actor=user
    )
    return [ScoringRuleOut.model_validate(r).model_dump(mode="json") for r in rules], 200


@projects_bp.route(_SBASE, methods=["POST"])
@auth.require_auth()
def create_scoring_rule(project_ref: str, survey_id: int, version_number: int):
    payload = parse(CreateScoringRuleRequest, request)
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    rule = content_svc.create_scoring_rule(
        db=db, project_id=project_id, survey_id=survey_id, version_number=version_number, data=payload, actor=user
    )
    return ScoringRuleOut.model_validate(rule).model_dump(mode="json"), 201


@projects_bp.route(f"{_SBASE}/<int:scoring_rule_id>", methods=["PATCH"])
@auth.require_auth()
def update_scoring_rule(project_ref: str, survey_id: int, version_number: int, scoring_rule_id: int):
    payload = parse(UpdateScoringRuleRequest, request)
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    rule = content_svc.update_scoring_rule(
        db=db,
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        scoring_rule_id=scoring_rule_id,
        data=payload,
        actor=user,
    )
    return ScoringRuleOut.model_validate(rule).model_dump(mode="json"), 200


@projects_bp.route(f"{_SBASE}/<int:scoring_rule_id>", methods=["DELETE"])
@auth.require_auth()
def delete_scoring_rule(project_ref: str, survey_id: int, version_number: int, scoring_rule_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    content_svc.delete_scoring_rule(
        db=db,
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        scoring_rule_id=scoring_rule_id,
        actor=user,
    )
    return {"message": "Scoring rule deleted"}, 200
