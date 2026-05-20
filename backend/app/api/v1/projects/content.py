from flask import request

from app.api.utils.validation import parse
from app.api.v1.projects import content_svc, projects_bp, users_service
from app.api.v1.projects.resolver import resolve_project_ref
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
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


@openapi_route(summary="List survey content nodes", response_model=list[NodeOut], tags=["Survey Content"])
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


@openapi_route(
    summary="Create survey content node",
    request_model=CreateNodeRequest,
    response_model=NodeOut,
    status_code=201,
    tags=["Survey Content"],
)
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


@openapi_route(summary="Get survey content node", response_model=NodeOut, tags=["Survey Content"])
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


@openapi_route(
    summary="Update survey content node",
    request_model=UpdateNodeRequest,
    response_model=NodeOut,
    tags=["Survey Content"],
)
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


@openapi_route(summary="Delete survey content node", tags=["Survey Content"], status_code=204)
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
    return "", 204


# ── Scoring rules ─────────────────────────────────────────────────────────────


@openapi_route(summary="List scoring rules", response_model=list[ScoringRuleOut], tags=["Scoring Rules"])
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


@openapi_route(
    summary="Create scoring rule",
    request_model=CreateScoringRuleRequest,
    response_model=ScoringRuleOut,
    status_code=201,
    tags=["Scoring Rules"],
)
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


@openapi_route(
    summary="Update scoring rule",
    request_model=UpdateScoringRuleRequest,
    response_model=ScoringRuleOut,
    tags=["Scoring Rules"],
)
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


@openapi_route(summary="Delete scoring rule", tags=["Scoring Rules"], status_code=204)
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
    return "", 204
