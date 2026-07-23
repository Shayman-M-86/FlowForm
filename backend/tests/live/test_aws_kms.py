"""Read/write crypto smoke test against a deliberately selected real KMS key."""

from __future__ import annotations

import os

import boto3
import pytest

from app.crypto._internal.kms_context import build_survey_kms_context
from app.crypto._internal.wrapping import unwrap_survey_key, wrap_survey_key
from app.crypto.models import PlaintextSurveyKey
from tests.live.helpers import require_live_env

pytestmark = pytest.mark.live_external


def test_survey_key_wrap_unwrap_via_live_kms() -> None:
    kms_key_arn = require_live_env("FLOWFORM_LIVE_AWS_KMS_KEY_ARN")
    region = os.environ.get("AWS_REGION", "ap-southeast-2")
    kms_client = boto3.client("kms", region_name=region)
    survey_key = PlaintextSurveyKey(os.urandom(32))
    context = build_survey_kms_context(project_id=1, survey_id=1)

    wrapped = wrap_survey_key(survey_key, kms_key_arn, context, client=kms_client)
    assert wrapped != survey_key

    unwrapped = unwrap_survey_key(wrapped, kms_key_arn, context, client=kms_client)
    assert unwrapped == survey_key
