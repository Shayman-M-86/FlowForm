"""Generate a standalone survey draft from a prompt."""

from flask import Blueprint, request

from app.api.utils.serialization import serialize
from app.api.utils.validation import parse
from app.core.extensions import auth
from app.openapi import openapi_route
from app.schema.api.requests.ai_import import AIImportRequest
from app.schema.api.responses.ai_import import AIImportResponse
from app.services.openai import get_openai_service

studio_ai_import_bp = Blueprint("studio_ai_import_v1", __name__)


@openapi_route(
    summary="Generate a survey draft with AI",
    request_model=AIImportRequest,
    response_model=AIImportResponse,
    error_statuses=(502, 503),
    tags=["Survey Builder"],
)
@studio_ai_import_bp.post("/surveys/ai-import")
@auth.require_auth()
def generate_ai_import():
    payload = parse(AIImportRequest, request)
    content = get_openai_service().generate(payload.prompt)
    return serialize(AIImportResponse, AIImportResponse(content=content)), 200
