---
title: Surveys and versioning
aliases:
  - "Surveys and versioning"
document_type: domain
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
related_code:
  - "../../backend/app/services/surveys.py"
  - "../../backend/app/domain/version_rules.py"
  - "../../backend/app/schema/orm/core/survey.py"
  - "../../backend/app/repositories/surveys_repo.py"
  - "../../backend/tests/integration/core/test_survey_version_lifecycle.py"
  - "../../infra/database/init/schema/flowform_core_db_schema_v4.sql"
related_docs:
  - "Projects and access"
  - "Builder and rules"
  - "Submissions"
---

# Surveys and versioning

Defines the durable survey container, its immutable publication snapshots, and
the lifecycle that binds respondent attempts to exact content. Editing questions
and rules is described by [[builder-and-rules|Builder and rules]].

## Purpose

Versioning lets authors continue changing a survey without changing the content
seen by an existing submission session. The survey owns stable settings and a
pointer to the active published version; each version owns one ordered content
snapshot and its publication state.

## Responsibilities

- Maintain project-scoped surveys, titles, visibility, public slugs, default
  response stores, and the active published-version pointer.
- Create monotonically numbered draft versions and copy an existing version's
  nodes and scoring rules into a new draft.
- Restrict node and scoring-rule mutations to draft versions.
- Publish a draft by compiling its ordered nodes and scoring rules, ensuring a
  response store and survey encryption key exist, and making it the active
  published version.
- Archive versions and safely clear the active pointer when the current
  published version is archived.
- Pin each submission session to the version selected at session start.

## Non-responsibilities

- This domain does not define question-family fields or execute branching rules.
- It does not decide which Studio member may edit or publish; permissions belong
  to [[projects-and-access|Projects and access]].
- It does not resolve respondent access or subjects.
- It does not store answer values or manage the response encryption hierarchy.

## Main entities and invariants

| Entity | Current state | Important invariant |
| --- | --- | --- |
| Survey | `private`, `link_only`, or `public` visibility | A public survey must have a public slug, and a slug is permitted only for public visibility. |
| Survey version | `draft`, `published`, or `archived` | Version numbers are positive and unique per survey; at most one non-deleted published version exists. |
| Active version pointer | `surveys.published_version_id` | Must reference a published, non-deleted version of the same survey. |
| Compiled schema | JSON snapshot on a published version | Published state requires both compiled schema and publication timestamp. |
| Response store | Project-scoped destination selected by the survey | The default store must belong to the same project. |
| Survey encryption key | One KMS-wrapped branch key per survey | Created as a publication prerequisite and bound to project/survey context. |

Database triggers prevent mutation of nodes and scoring rules belonging to a
published version and protect an active published version from being archived or
deleted before its survey pointer is cleared. Submission foreign keys prevent a
session from pointing to a version belonging to another survey.

## Important workflows

1. Survey creation ensures a primary platform response store exists and records
   it as the survey default.
2. Version creation chooses the current maximum version number plus one and
   starts the new version as a draft.
3. Copy-to-draft clones question nodes, rule nodes, and scoring rules while
   assigning a new version number and new database identities.
4. Publication verifies draft state and non-empty node content, builds the
   compiled `nodes` and `scoring_rules` snapshot, creates missing storage/key
   prerequisites, archives the prior published version, and moves the survey
   pointer to the new one.
5. Session start resolves only a published version and stores its ID on the
   submission session; subsequent authoring does not rebind that attempt.

## Implementation map

- `backend/app/services/surveys.py` owns survey and version lifecycle
  orchestration, compilation, and publication prerequisites.
- `backend/app/domain/version_rules.py` and `survey_rules.py` contain application
  lifecycle and visibility guards.
- `backend/app/repositories/surveys_repo.py` implements version numbering and
  the ordered pointer/status updates needed when publishing or archiving.
- `backend/app/schema/orm/core/survey.py` maps the survey and version records;
  the core SQL schema owns the definitive checks, unique indexes, foreign keys,
  and publication-protection triggers.
- Integration tests cover replacing an active version, archiving it, copying all
  content types, and translating trigger failures.

## Verified gaps and open questions

- The publication non-empty check currently uses all nodes, so a draft containing
  only rule nodes can pass even though no respondent question exists.
- Publication validates each request shape but does not perform a whole-graph
  check for missing rule targets, backward loops, or unreachable questions.
- Compiled schema is assembled as a JSON dictionary in the service; no explicit
  versioned compiled-schema model or migration contract was found.
- The repository permits deleting a survey even when it is published. Core rows
  cascade, but response-side ciphertext cleanup is not part of that transaction.
- Version creation calculates `max(version_number) + 1` without an explicit row
  lock. The unique constraint catches collisions, but no retry is implemented.

## Related documents

- [[projects-and-access|Projects and access]]
- [[builder-and-rules|Builder and rules]]
- [[submissions|Submissions]]
