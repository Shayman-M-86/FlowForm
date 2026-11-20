"""Canonical survey document hierarchy, independent of transport and storage."""

from typing import Annotated, Literal

from pydantic import Field

from app.schema.enums import NoticeTone
from app.schema.models.common.base import DataModel
from app.schema.models.survey_document.conditions import SurveyWorkflow
from app.schema.models.survey_document.fields import SurveyField
from app.schema.types import (
    ContentText,
    HeadingLevel,
    LimitedList,
    LongString,
    NoticeTitle,
    ReadableId,
    SectionTitle,
    SurveyBlocks,
    SurveyTitle,
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


class SurveyContent(DataModel):
    """Portable authored survey content."""

    title: SurveyTitle
    description: LongString | None = None
    sections: LimitedList[SurveySection]
    workflow: SurveyWorkflow | None = None
