"""Shared Literal enums for API request/response schemas.

Mirrors the values enforced by DB CHECK constraints. Defined here (not in
the ORM layer) because the schema layer must not import from models per
the project layer rules.

When the DB constraint changes, update the matching Literal here so the
OpenAPI spec and any generated TypeScript clients stay accurate.
"""

from __future__ import annotations

from typing import Literal

SurveyVisibility = Literal["private", "link_only", "public"]
SurveyVersionStatus = Literal["draft", "published", "archived"]
SurveyNodeType = Literal["question", "rule"]
SubmissionChannel = Literal["link", "slug", "system"]
SubmissionStatus = Literal["pending", "stored", "failed"]
AnswerFamily = Literal["choice", "field", "matching", "rating"]
