---
title: Surveys and versioning
aliases: ["Surveys and versioning"]
document_type: domain
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-11-20
tags: [backend]
related_code:
  - "../../../backend/app/services/surveys.py"
  - "../../../backend/app/services/content.py"
  - "../../../backend/app/domain/version_rules.py"
  - "../../../backend/app/schema/orm/core/survey.py"
  - "../../../backend/app/repositories/surveys_repo.py"
  - "../../../backend/app/db/json_types.py"
  - "../../../backend/tests/integration/core/test_survey_version_lifecycle.py"
related_docs:
  - "Backend knowledge"
  - "Projects and access"
  - "Builder and rules"
  - "Submissions"
---

# Surveys and versioning

This draft owns a survey's durable container, its immutable publication
snapshots, and the lifecycle that pins a respondent attempt to exact content.
Editing nodes and rule semantics belongs to [[builder-and-rules|Builder and rules]].

The current model distinguishes draft, published, and archived versions.
Authoring changes belong to a draft; publication assembles a compiled snapshot,
selects the active version, and establishes response-store/encryption
prerequisites. A submission session captures the selected published version, so
later authoring does not alter an in-progress attempt.

```text
survey
  |
  v
draft version --edit--> draft version --publish--> published snapshot
                                                   |
                                                   +--> active version
                                                   |
                                                   +--> submission session
                                                        pins this snapshot

published snapshot --replace/archive--> historical immutable version
```

Project permissions control who may perform these operations, while respondent
entry and answer persistence are separate boundaries. The service, repository,
ORM, SQL, and lifecycle-test paths in the front matter identify the source to
check before promoting this draft.

## Survey content and version metadata

A `SurveyVersion` row owns the database ID, survey ID, version number, revision,
and lifecycle state. Its nullable `content` JSONB column holds `SurveyContent`,
with title, optional description, ordered sections and optional workflow. Empty
drafts start at revision zero. Copying content into a new draft starts that
draft at revision one and preserves field UUIDs.

Studio selects versions from a metadata list and reads a specific version by
version number. To save content it sends `PUT /versions/{version_id}/content`
under the survey resource with the expected revision and the complete content.
The service locks the scoped version row, checks draft status and revision,
then updates the content and revision together. The response returns the new
revision. A stale save returns 409.

Publication locks the version while validating that its content exists, field
UUIDs are unique, and conditions reference fields in the same version. SQL
requires content and a timestamp for publication and locks the content and
revision after the version leaves draft. Respondent discovery returns the
published version ID and content. Field lookup uses the pinned version's content.

Studio's authenticated `POST /api/v1/studio/surveys/ai-import` accepts a prompt
and returns a draft as `SurveyContent`. It includes the title, optional
description, sections and optional workflow shared by saved definitions. A
caller can use it before a survey or project has been selected. Version metadata
belongs to the separate save flow. The common error handler returns 503 when
generation is disabled and 502 when an upstream call yields no usable draft.

## Related documents

- [[backend-index|Backend knowledge]]
- [[projects-and-access|Projects and access]]
- [[submissions|Submissions]]
- [[builder-and-rules|Builder and rules]]
