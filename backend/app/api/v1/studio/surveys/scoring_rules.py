from flask import g, request

from app.api.utils.serialization import serialize
from app.api.utils.validation import parse
from app.api.v1.studio.projects import content_svc, studio_projects_bp
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.content import CreateScoringRuleRequest, UpdateScoringRuleRequest
from app.schema.api.responses.content import ScoringRuleResponses
from app.services.access.access_service import require_survey_permission

_BASE = "/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>/scoring-rules"


@openapi_route(summary="List scoring rules", response_model=list[ScoringRuleResponses], tags=["Survey Scoring"])
@studio_projects_bp.route(_BASE, methods=["GET"])
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
    tags=["Survey Scoring"],
)
@studio_projects_bp.route(_BASE, methods=["POST"])
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
    tags=["Survey Scoring"],
)
@studio_projects_bp.route(f"{_BASE}/<bint:scoring_rule_id>", methods=["PATCH"])
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


@openapi_route(summary="Delete scoring rule", tags=["Survey Scoring"], status_code=204)
@studio_projects_bp.route(f"{_BASE}/<bint:scoring_rule_id>", methods=["DELETE"])
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
