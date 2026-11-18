"""Stable response-store identity."""

from typing import Annotated

from pydantic import Field

from app.schema.models.common.types import DatabaseIdentity

ResponseStoreId = Annotated[DatabaseIdentity, Field(description="Response store identity")]
