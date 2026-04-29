from flask import request

from app.api.utils.validation import parse
from app.api.v1.projects import content_svc, projects_bp, users_service
from app.api.v1.projects.resolver import resolve_project_ref
from app.core.extensions import auth
from app.db.context import get_core_db
from app.schema.api.requests.content import (
    CreateNodeRequest,
    CreateScoringRuleRequest,
    UpdateNodeRequest,
    UpdateScoringRuleRequest,
)
from app.schema.api.responses.content import NodeOut, ScoringRuleOut
from app.schema.orm.core.user import User

_NBASE = "/<project_ref>/surveys/<int:survey_id>/versions/<int:version_number>/nodes"
_SBASE = "/<project_ref>/surveys/<int:survey_id>/versions/<int:version_number>/scoring-rules"


# ── Nodes ─────────────────────────────────────────────────────────────────────


@projects_bp.route(_NBASE, methods=["GET"])
@auth.require_auth()
def list_nodes(project_ref: str, survey_id: int, version_number: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    nodes = content_svc.list_nodes(
        db=db, project_id=project_id, survey_id=survey_id, version_number=version_number, actor=user
    )
    return [NodeOut.model_validate(n).model_dump(mode="json") for n in nodes], 200


@projects_bp.route(_NBASE, methods=["POST"])
@auth.require_auth()
def create_node(project_ref: str, survey_id: int, version_number: int):
    payload = parse(CreateNodeRequest, request)
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    node = content_svc.create_node(
        db=db, project_id=project_id, survey_id=survey_id, version_number=version_number, data=payload, actor=user
    )
    return NodeOut.model_validate(node).model_dump(mode="json"), 201


@projects_bp.route(f"{_NBASE}/<int:node_id>", methods=["GET"])
@auth.require_auth()
def get_node(project_ref: str, survey_id: int, version_number: int, node_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    node = content_svc.get_node(
        db=db,
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        node_id=node_id,
        actor=user,
    )
    return NodeOut.model_validate(node).model_dump(mode="json"), 200


@projects_bp.route(f"{_NBASE}/<int:node_id>", methods=["PATCH"])
@auth.require_auth()
def update_node(project_ref: str, survey_id: int, version_number: int, node_id: int):
    payload = parse(UpdateNodeRequest, request)
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    node = content_svc.update_node(
        db=db,
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        node_id=node_id,
        data=payload,
        actor=user,
    )
    return NodeOut.model_validate(node).model_dump(mode="json"), 200


@projects_bp.route(f"{_NBASE}/<int:node_id>", methods=["DELETE"])
@auth.require_auth()
def delete_node(project_ref: str, survey_id: int, version_number: int, node_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    content_svc.delete_node(
        db=db,
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        node_id=node_id,
        actor=user,
    )
    return {"message": "Node deleted"}, 200


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
