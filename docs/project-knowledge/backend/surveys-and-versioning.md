---
title: Surveys and versioning
aliases: ["Surveys and versioning"]
document_type: domain
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-11-19
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

## Definition persistence during migration

The survey-version document is a `SurveyDefinition`, stored as JSONB through
`SurveyDefinitionJSONB`. The conversion serializes JSON-compatible values on
write and reconstructs the model on load. Empty drafts may have no definition.

`surveys_repo.get_definition` scopes retrieval to project, survey, and version
number, excludes soft-deleted versions, and returns an independent snapshot.
`update_definition` replaces the complete document and flushes without committing;
the calling service owns the transaction. Explicit replacement also persists
nested model edits, which SQLAlchemy does not otherwise track automatically.

Services own authorization, draft editability, document/version identity,
revision policy, and publication validation. Field lookup is document traversal;
saved-answer retrieval remains a response-repository operation. The legacy
node-based editing, cloning/publication, and respondent/reporting services are
not yet fully migrated to these boundaries.

`ContentService.update_definition` now provides the draft-editability guard and
transaction for a whole-document update. It obtains the project/survey-scoped
version, rejects non-drafts, saves through the repository, and commits. Survey
permission enforcement belongs to its caller. The old node/scoring-rule routes
and AI-preview entry point still need replacement or relocation; their former
methods no longer exist on `ContentService`.

## Related documents

- [[backend-index|Backend knowledge]]
- [[projects-and-access|Projects and access]]
- [[submissions|Submissions]]
- [[builder-and-rules|Builder and rules]]
