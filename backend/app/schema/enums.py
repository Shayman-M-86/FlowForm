"""Shared Literal enums for the schema layer.

Mirrors the values enforced by DB CHECK constraints. Defined here, below both
the ORM and API schema sub-layers, so each can import these aliases without
crossing sideways into the other (ORM must not import from api/, and api/ must
not import from orm/). These are plain Literal aliases, not Postgres ENUM
types — the DB columns stay TEXT/varchar with CHECK constraints.

When a DB constraint changes, update the matching Literal here so the ORM
mappings, the OpenAPI spec, and any generated TypeScript clients stay accurate.
"""

from __future__ import annotations

from typing import Literal

ProjectMemberStatus = Literal["active", "suspended"]
ProjectInvitationStatus = Literal["pending", "accepted", "declined", "revoked"]
ResponseStoreType = Literal["platform_postgres", "external_postgres"]
SurveyVisibility = Literal["private", "link_only", "public"]
SurveyLinkType = Literal["general", "private", "authenticated"]
SurveyLinkAssignmentSource = Literal["manual", "automated"]
SurveyVersionStatus = Literal["draft", "published", "archived"]
SubjectIdentityType = Literal["email", "authenticated_user"]
SubjectIdentityVerificationStatus = Literal["unverified", "verified"]
CanonicalSubjectFilter = Literal["canonical", "alias", "all"]
SubmissionChannel = Literal["link", "slug", "system"]
SubmissionStatus = Literal["pending", "stored", "failed"]
SubmissionSessionStatus = Literal["in_progress", "completed", "abandoned"]
SubmissionEventType = Literal["session_started", "field_viewed", "answer_saved", "session_completed"]
SubmissionAnswerState = Literal["answered", "cleared"]
ExportFormat = Literal["csv", "json"]

# Survey presentation vocabularies.
NoticeTone = Literal["info", "success", "warning", "error"]
NumberPresentation = Literal["input", "stepper"]
RatingPresentation = Literal["slider", "stars", "scale"]
SingleChoicePresentation = Literal["radio", "dropdown", "buttons", "cards"]
MultipleChoicePresentation = Literal["checkboxes", "buttons", "cards"]
BooleanPresentation = Literal["yes_no", "toggle"]
DatePresentation = Literal["calendar", "input"]

# Submission workflow decisions shared by internal result models.
type SubjectResolutionSource = Literal[
    "assigned_link",
    "authenticated_user",
    "recognition_token",
    "anonymous_created",
    "none",
]

type SubmissionAccessMethod = Literal[
    "public_slug",
    "general_link",
    "private_link",
    "authenticated_assigned_link",
]

type TokenAction = Literal["issue", "rotate", "keep", "mark_used", "none"]
