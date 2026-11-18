from app.schema import limits
from app.schema.api.common.base import APIRequestModel
from app.schema.api.common.types import PageNumber, PageSize, SearchText
from app.schema.types import EmailAddress, SubjectCode


class ListProjectParticipantsRequest(APIRequestModel):
    """Query params for listing a project's participants."""

    search: SearchText | None = None
    page: PageNumber = limits.LIST_PAGE_DEFAULT
    page_size: PageSize = limits.LIST_PAGE_SIZE_DEFAULT


class CreateParticipantRequest(APIRequestModel):
    """Request body for creating a participant (subject + email identity + participant)."""

    email: EmailAddress
    subject_code: SubjectCode | None = None


class UpdateParticipantRequest(APIRequestModel):
    """Request body for updating a participant's assigned email and/or subject code."""

    email: EmailAddress | None = None
    subject_code: SubjectCode | None = None
