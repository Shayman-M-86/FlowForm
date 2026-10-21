---
title: Surveys and versioning
aliases: ["Surveys and versioning"]
document_type: domain
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-10-21
tags: [backend]
related_code:
  - "../../../backend/app/services/surveys.py"
  - "../../../backend/app/domain/version_rules.py"
  - "../../../backend/app/schema/orm/core/survey.py"
  - "../../../backend/app/repositories/surveys_repo.py"
  - "../../../backend/tests/integration/core/test_survey_version_lifecycle.py"
related_docs:
  - "Backend knowledge"
  - "Projects and access"
  - "Builder and rules"
  - "Submissions"
---

# Surveys and versioning

This page describes a survey's durable container, its immutable publication
snapshots, and the lifecycle that pins a respondent attempt to exact content.
The authoring experience is described in [[builder-and-rules|Builder and rules]];
that frontend is still being migrated to the document model.

The current model distinguishes draft, published, and archived versions.
Each version stores one canonical survey document and a revision. Creating a
version supplies its definition; replacing a draft definition increments the
revision. Publication checks the stored document, selects the active version,
and establishes response-store/encryption prerequisites. A submission session captures the selected published version, so
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

Draft replacement is guarded by survey edit permission and draft status.
Published definitions are protected against changes in both the service layer
and database. Copying a version creates a new draft from the complete definition.
The revision is currently a change counter, not a concurrent-edit conflict check.

## Related documents

- [[backend-index|Backend knowledge]]
- [[projects-and-access|Projects and access]]
- [[submissions|Submissions]]
- [[builder-and-rules|Builder and rules]]
