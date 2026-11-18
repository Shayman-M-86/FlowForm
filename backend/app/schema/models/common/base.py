"""Default Pydantic limits shared by data and HTTP models."""

from pydantic import BaseModel, ConfigDict

from app.schema import limits


class SchemaModel(BaseModel):
    """Default string ceiling without changing text whitespace."""

    model_config = ConfigDict(str_max_length=limits.DEFAULT_STRING_MAX, allow_inf_nan=False)


class DataModel(SchemaModel):
    """Reusable data structures reject unknown properties."""

    model_config = ConfigDict(extra="forbid", serialize_by_alias=True)
