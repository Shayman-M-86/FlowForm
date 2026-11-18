"""HTTP boundary defaults, separate from shared data model configuration."""

from pydantic import ConfigDict

from app.schema.models.common.base import DataModel, SchemaModel


class APIRequestModel(DataModel):
    """Requests reject unknown properties and inherit schema string defaults."""


class APIResponseModel(SchemaModel):
    """Responses can read ORM attributes while ignoring unrelated properties."""

    model_config = ConfigDict(from_attributes=True)
