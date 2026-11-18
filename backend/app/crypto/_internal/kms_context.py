"""KMS encryption context for survey key wrap/unwrap.

The context binds a wrapped survey key to its survey. KMS refuses to
unwrap unless the same context is supplied, so a key wrapped for one
survey cannot be unwrapped under another.
"""

from __future__ import annotations

from app.schema.types import ProjectId, SurveyId

SURVEY_KMS_CONTEXT_VERSION = 1


def build_survey_kms_context(
    *,
    project_id: ProjectId,
    survey_id: SurveyId,
    kms_context_version: int = SURVEY_KMS_CONTEXT_VERSION,
) -> dict[str, str]:
    """Build the KMS encryption context binding a survey key to its survey."""
    return {
        "purpose": "survey_branch_key",
        "project_id": str(project_id),
        "survey_id": str(survey_id),
        "kms_context_version": str(kms_context_version),
    }
