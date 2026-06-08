from flask import g, request


from app.api.utils.serialization import serialize
from app.api.utils.validation import parse
from app.api.v1.projects import content_svc, projects_bp
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.content import (
    CreateNodeRequest,
    CreateScoringRuleRequest,
    UpdateNodeRequest,
    UpdateScoringRuleRequest,
)
from app.schema.api.responses.content import NodeResponses, ScoringRuleResponses
from app.services.access.access_service import require_survey_permission

_NBASE = "/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>/nodes"
_SBASE = "/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>/scoring-rules"


# ── Nodes ─────────────────────────────────────────────────────────────────────


@openapi_route(summary="List survey content nodes", response_model=list[NodeResponses], tags=["Survey Content"])
@projects_bp.route(_NBASE, methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.view)
def list_nodes(project_id: int, survey_id: int, version_number: int):
    nodes = content_svc.list_nodes(
        db=get_core_db(), project_id=project_id, survey_id=survey_id, version_number=version_number, actor=g.actor
    )
    return [serialize(NodeResponses, n) for n in nodes], 200


@openapi_route(
    summary="Create survey content node",
    request_model=CreateNodeRequest,
    response_model=NodeResponses,
    status_code=201,
    tags=["Survey Content"],
)
@projects_bp.route(_NBASE, methods=["POST"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def create_node(project_id: int, survey_id: int, version_number: int):
    payload = parse(CreateNodeRequest, request)
    node = content_svc.create_node(
        db=get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        data=payload,
        actor=g.actor,
    )
    return serialize(NodeResponses, node), 201


@openapi_route(summary="Get survey content node", response_model=NodeResponses, tags=["Survey Content"])
@projects_bp.route(f"{_NBASE}/<bint:node_id>", methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.view)
def get_node(project_id: int, survey_id: int, version_number: int, node_id: int):
    node = content_svc.get_node(
        db=get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        node_id=node_id,
        actor=g.actor,
    )
    return serialize(NodeResponses, node), 200


@openapi_route(
    summary="Update survey content node",
    request_model=UpdateNodeRequest,
    response_model=NodeResponses,
    tags=["Survey Content"],
)
@projects_bp.route(f"{_NBASE}/<bint:node_id>", methods=["PATCH"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def update_node(project_id: int, survey_id: int, version_number: int, node_id: int):
    payload = parse(UpdateNodeRequest, request)
    node = content_svc.update_node(
        db=get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        node_id=node_id,
        data=payload,
        actor=g.actor,
    )
    return serialize(NodeResponses, node), 200


@openapi_route(summary="Delete survey content node", tags=["Survey Content"], status_code=204)
@projects_bp.route(f"{_NBASE}/<bint:node_id>", methods=["DELETE"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def delete_node(project_id: int, survey_id: int, version_number: int, node_id: int):
    content_svc.delete_node(
        db=get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        node_id=node_id,
        actor=g.actor,
    )
    return "", 204


# ── Scoring rules ─────────────────────────────────────────────────────────────


@openapi_route(summary="List scoring rules", response_model=list[ScoringRuleResponses], tags=["Scoring Rules"])
@projects_bp.route(_SBASE, methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.view)
def list_scoring_rules(project_id: int, survey_id: int, version_number: int):
    rules = content_svc.list_scoring_rules(
        db=get_core_db(), project_id=project_id, survey_id=survey_id, version_number=version_number, actor=g.actor
    )
    return [serialize(ScoringRuleResponses, r) for r in rules], 200


@openapi_route(
    summary="Create scoring rule",
    request_model=CreateScoringRuleRequest,
    response_model=ScoringRuleResponses,
    status_code=201,
    tags=["Scoring Rules"],
)
@projects_bp.route(_SBASE, methods=["POST"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def create_scoring_rule(project_id: int, survey_id: int, version_number: int):
    payload = parse(CreateScoringRuleRequest, request)
    rule = content_svc.create_scoring_rule(
        db=get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        data=payload,
        actor=g.actor,
    )
    return serialize(ScoringRuleResponses, rule), 201


@openapi_route(
    summary="Update scoring rule",
    request_model=UpdateScoringRuleRequest,
    response_model=ScoringRuleResponses,
    tags=["Scoring Rules"],
)
@projects_bp.route(f"{_SBASE}/<bint:scoring_rule_id>", methods=["PATCH"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def update_scoring_rule(project_id: int, survey_id: int, version_number: int, scoring_rule_id: int):
    payload = parse(UpdateScoringRuleRequest, request)
    rule = content_svc.update_scoring_rule(
        db=get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        scoring_rule_id=scoring_rule_id,
        data=payload,
        actor=g.actor,
    )
    return serialize(ScoringRuleResponses, rule), 200


@openapi_route(summary="Delete scoring rule", tags=["Scoring Rules"], status_code=204)
@projects_bp.route(f"{_SBASE}/<bint:scoring_rule_id>", methods=["DELETE"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def delete_scoring_rule(project_id: int, survey_id: int, version_number: int, scoring_rule_id: int):
    content_svc.delete_scoring_rule(
        db=get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        scoring_rule_id=scoring_rule_id,
        actor=g.actor,
    )
    return "", 204
