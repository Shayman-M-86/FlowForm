"""Canonical survey document hierarchy, independent of transport and storage."""

from typing import Annotated, Literal

from pydantic import Field

from app.schema.enums import NoticeTone, SurveyVersionStatus
from app.schema.models.common.base import DataModel
from app.schema.models.survey.conditions import SurveyWorkflow
from app.schema.models.survey.fields import SurveyField
from app.schema.types import (
    ContentText,
    DocumentRevision,
    HeadingLevel,
    LimitedList,
    LongString,
    NoticeTitle,
    ProjectName,
    ReadableId,
    SectionTitle,
    SurveyBlocks,
    SurveyTitle,
    SurveyVersionId,
)


class HeadingContent(DataModel):
    """Heading text and level."""

    text: ContentText
    level: HeadingLevel


class TextContent(DataModel):
    """Paragraph text."""

    text: ContentText


class NoticeContent(DataModel):
    """Notice presentation and text."""

    tone: NoticeTone
    title: NoticeTitle
    text: ContentText


class HeadingBlock(DataModel):
    """Heading content block."""

    id: ReadableId
    type: Literal["heading"]
    content: HeadingContent


class ParagraphBlock(DataModel):
    """Paragraph content block."""

    id: ReadableId
    type: Literal["paragraph"]
    content: TextContent


class NoticeBlock(DataModel):
    """Notice content block."""

    id: ReadableId
    type: Literal["notice"]
    content: NoticeContent


class DividerBlock(DataModel):
    """Visual separator."""

    id: ReadableId
    type: Literal["divider"]


class InputBlock(DataModel):
    """A block containing an answerable field."""

    id: ReadableId
    type: Literal["input"]
    field: SurveyField


Block = Annotated[
    HeadingBlock | ParagraphBlock | NoticeBlock | DividerBlock | InputBlock,
    Field(discriminator="type", title="SurveyBlock"),
]


class SurveySection(DataModel):
    """An ordered group of survey blocks."""

    id: ReadableId
    title: SectionTitle
    description: LongString | None = None
    blocks: SurveyBlocks[Block]


class SurveyDocument(DataModel):
    """Ordered survey sections."""

    sections: LimitedList[SurveySection]


class SurveyDefinition(DataModel):
    """Canonical FlowForm V2 survey definition."""

    id: ReadableId
    versionId: SurveyVersionId
    revision: DocumentRevision
    title: SurveyTitle
    description: LongString | None = None
    projectName: ProjectName
    status: SurveyVersionStatus
    document: SurveyDocument
    workflow: SurveyWorkflow | None = None
