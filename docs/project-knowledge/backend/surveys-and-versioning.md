---
title: Surveys and versioning
aliases: ["Surveys and versioning"]
document_type: domain
status: verified
authority: canonical
verified_evidence_digest: sha256:82649bcb08dbd5a5a4ffaf7ac679d3c4f53b1e2934e3f9d25e9de895e2f6aa78
last_edited: 2026-09-05
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

## Related documents

- [[backend-index|Backend knowledge]]
- [[projects-and-access|Projects and access]]
- [[submissions|Submissions]]
- [[builder-and-rules|Builder and rules]]
