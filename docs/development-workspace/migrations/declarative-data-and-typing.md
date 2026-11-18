---
title: Declarative data and typing migration
aliases: ["Declarative data and typing migration"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-11-19
tags: [backend, frontend]
related_code:
  - "../../../backend/app/schema/README.md"
  - "../../../backend/app/db/base.py"
  - "../../../backend/app/schema/types.py"
  - "../../../backend/app/db/type_mapping.py"
  - "../../../backend/app/openapi/README.md"
related_docs: ["Engineering migrations", "FlowForm V2 survey document definition", "FlowForm V2 answer data definition"]
---

# Declarative data and typing migration

FlowForm is moving toward data structures whose meaning, allowed values, and
construction rules can be understood from their declarations. Each meaningful
value has an authoritative type, shared by the layers that handle that same
value. Request parsing, services, persistence, response serialization, and
OpenAPI should describe a consistent contract.

This is an active migration. Shared schemas and ORM construction have advanced
ahead of some application callers. This document records the direction and
current verification boundary; it does not certify the complete application.

## Declare the meaning of a value once

A project reference uses `ProjectId`, a survey-version reference uses
`SurveyVersionId`, and an answer references `SurveyFieldUuid` and
`ClientMutationId`. These semantic names remain useful even where several
identifiers share the same underlying integer or UUID representation.

Trace a value from its source before assigning a shared type. Matching names or
primitive representations alone do not establish that two values are the same
identity. In particular, Auth0 subjects, local user IDs, public identifiers,
version identities, version numbers, and revisions have different meanings.

Reuse is encouraged across API, service, repository, ORM, and context boundaries.
A meaningful type does not need multiple existing consumers to justify its
central definition. Existing value types are reused before new ones are added.

## Give each declaration an owner

| Concern | Owner |
| --- | --- |
| Shared identities, text, timestamps, email, counts, and collection types | `schema/types.py`, grouped by domain |
| Shared value normalization and parsing | `schema/validators.py` |
| Fixed status and presentation vocabularies | `schema/enums.py` |
| Shared data structures | Domain models under `schema/models/` |
| HTTP-specific controls such as pagination and search | `schema/api/common/` |
| Request and response composition | `schema/api/requests/` and `schema/api/responses/` |
| SQL storage and relationships | `schema/orm/` |
| SQL storage mapping for shared nominal identities | `db/type_mapping.py` |
| Broad resource ceilings and pagination defaults | `schema/limits.py` |

Shared domain models do not import HTTP contracts or ORM mappings. Promote a
value out of API ownership when persistence or application logic also uses it.

## Define shapes and constraints declaratively

Named `Annotated` types own normalization, bounds, and formats. Model properties
reference those types and declare requiredness, defaults, and aliases. Constrain
text categories, presentation vocabularies, and structured values explicitly.
String rules consistently use `StringConstraints`; numeric and collection rules
use `Field`. Shared metadata such as `DATABASE_ID_CONSTRAINTS` is defined once
and reused without mutation. Property defaults and aliases stay on models.
Use discriminated variants where a field selects a different valid object shape.
Reserve validators for relationships such as ordered bounds or dynamically
checking a submitted value against its answer specification.

Arbitrary dictionaries and recursive JSON require a real extensibility boundary.
Survey content and answers should describe their supported structures. Authored
answer bounds are serialized data models; they are not replacements for
Pydantic's constraint helpers.

Global limits express resource controls and shared settings. One-off business
bounds belong in their owning value type. Complete result collections should
represent the actual results; paginate retrieval rather than inventing generic
response-size caps.

## Let ORM mappings generate checked constructors

`CoreBase` and `ResponseBase` enable SQLAlchemy's native dataclass integration.
Mapped classes explicitly declare `kw_only=True` for consistent runtime and
Pyright interpretation. Their mapped declarations generate the constructor,
without a handwritten `__init__`, a forwarding dictionary, or an unset sentinel.

- Generated identities and database-owned timestamps use `init=False`.
- Relationships use `init=False`, so callers supply scalar foreign keys and
  relationship defaults cannot accidentally overwrite them.
- Nullable values declare `default=None`.
- Scalar construction defaults agree with domain and database defaults.
- Operation-owned timestamps remain accepted inputs. A creation-time UTC factory
  can supply their initial value when omitted.
- Existing recorded timestamps are returned from their source, including on retries.

Column SQL types, foreign keys, nullability, server defaults, constraints, and
indexes keep their storage responsibilities. Reusing a Pydantic value annotation
in `Mapped[...]` does not execute Pydantic validation during ORM assignment.
Storage-only hashes, encrypted payloads, keys, and raw serialized documents keep
appropriate storage types rather than acquiring unrelated API models.

## Make the types useful to tools

Meaningful identities use private `NewType` declarations and public annotated
aliases in the same shared module. For example:

```python
_ProjectId = NewType("_ProjectId", int)
type ProjectId = Annotated[_ProjectId, DATABASE_ID_CONSTRAINTS]
```

The private variable and `NewType` name match for Pyright. Public aliases keep
different identities statically distinct while preserving their integer, string,
or UUID wire representation. Ordinary constrained values need no nominal wrapper.
Both SQLAlchemy bases explicitly map the public identity aliases to SQL types.

Annotations and `NewType` calls do not validate ordinary Python arguments.
Use `TypeAdapter(...).validate_python(...)` or `Model.model_validate(...)` at
external boundaries and retain database safeguards. Direct Pydantic constructors
expect typed identities for static checking; raw input belongs in validation
methods. Services and repositories carry the same public aliases. Test fixtures
establish typed values explicitly rather than suppressing mismatches with casts.

Generated constructors must still expose the correct parameter names, primitive
types, requiredness, and defaults. Negative type checks should diagnose obsolete
keywords, misspellings, inappropriate generated-field arguments, and incompatible
value types. A generic `**kwargs: Any` signature does not provide that protection.

Top-level request variants use `Request`; request-owned models embedded in
another request use `NestedModel`. Shared domain models retain domain names.

## Derive OpenAPI from the same contracts

Flask route registration supplies paths and methods. Pydantic supplies schemas,
including input/output aliases, formats, bounds, requiredness, and discriminators.
Exported unions need stable titles. Referenced definitions must be registered,
and conflicting component definitions must fail explicitly.

The existing runtime error formatter owns `ErrorPayload`; OpenAPI derives its
error envelope from that typed contract. Documentation should not invent a
parallel runtime response model or manufacture business errors from guessed
constructor arguments. Common HTTP response component names remain deliberate
public metadata.

## Verify incrementally and report the boundary

Inspect one owner, search its consumers, trace conversions, change the shared
definition, update confirmed callers, and test before moving to the next group.
Checks include constructor signatures, negative static cases, serialization,
relationship persistence, generated schemas, and unchanged PostgreSQL DDL.

Current checks cover all 25 mapped constructors, invitation and participant
persistence smoke tests on adapted SQLite schemas, and OpenAPI builder/error
formatting cases. PostgreSQL DDL was compared across all 27 tables. These checks
do not establish a live PostgreSQL deployment or full application correctness.

Known runtime migration gaps include legacy node-model imports blocking full
route export, version creation that does not yet provide a V2 definition, and
event creation that still supplies the former question-node field. Do not hide
these gaps with permissive constructors, compatibility aliases, omitted routes,
or a success claim based only on isolated schema checks.

See [Schema conventions](../../../backend/app/schema/README.md) for the practical
review rules and [OpenAPI pipeline](../../../backend/app/openapi/README.md) for
export responsibilities.
