from app.schema import limits
from app.schema.api.common.base import APIRequestModel
from app.schema.enums import CanonicalSubjectFilter
from app.schema.types import PageNumber, PageSize, SearchText, SubjectCode


class ListProjectSubjectsRequest(APIRequestModel):
    """Query params for listing a project's subjects."""

    canonical_status: CanonicalSubjectFilter = "canonical"
    is_participant: bool | None = None
    search: SearchText | None = None
    page: PageNumber = limits.LIST_PAGE_DEFAULT
    page_size: PageSize = limits.LIST_PAGE_SIZE_DEFAULT


class UpdateSubjectRequest(APIRequestModel):
    """Request body for updating a subject's code."""

    subject_code: SubjectCode
