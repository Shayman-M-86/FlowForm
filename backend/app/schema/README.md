# Schema conventions

These conventions apply when defining or changing value types across FlowForm.

## Ownership

- `types.py` owns shared value definitions, grouped by domain: identities, text,
  timestamps, counts, email addresses, and collection bounds.
- `models/` owns complete reusable Pydantic data structures, organized by domain.
  `models/results/service_results.py` additionally owns internal service-result dataclasses.
- `models/survey_document/` owns the document, field, workflow, and answer shapes.
  `models/survey_access.py` separately owns visibility/public-slug variants;
  survey access metadata is not part of the survey document.
- `validators.py` owns shared scalar normalization and parsing helpers. Validators
  for complete structures remain beside their domain models.
- `api/common/types.py` owns HTTP-only values and request-only constraints.
  Promote a type into `types.py` when other layers need it. Page numbers and
  page sizes are shared with repositories; paginated HTTP result bounds remain
  in the API package.
- `api/requests/` and `api/responses/` own operation contracts.
- `orm/` owns SQLAlchemy mappings. Portable data models must not depend on API
  or ORM packages. Internal service-result dataclasses may carry existing ORM
  objects; import those annotations under `TYPE_CHECKING`, without loading
  mappings or adding Pydantic validation to service outcomes.
- `enums.py` owns enumerations shared across domains or persistence boundaries.
  This includes `CanonicalSubjectFilter`, used by queries and repositories.
- Shared search text and cryptographic byte labels live in `types.py` as they
  cross application and repository boundaries. Byte labels carry static meaning
  without imposing Pydantic constraints; crypto models re-export those same types.
- `PermissionName` composes the existing vocabulary in `domain/permissions.py`
  and is re-exported by `types.py`. Permission ORM rows remain `Permission`
  objects; their storage stays VARCHAR rather than an inferred SQL ENUM.

## Investigate before defining a type

1. Inspect the field's owning model and search its name and related type names
   across the schema directory.
2. Trace where the value is created, stored, passed, transformed, and serialized.
3. Determine whether matching names identify the same concept. Do not merge
   unrelated values merely because they are both strings, integers, or UUIDs.
4. Reuse the authoritative type, or define it once in the appropriate shared domain.
5. Update confirmed consumers incrementally and validate each affected boundary.

Reuse count is not the only criterion. A meaningful value such as an email,
field UUID, client mutation ID, or survey version ID deserves a named type even
when it initially has one consumer. Ordinary booleans and fixed discriminator
literals do not require artificial wrapper types.

## Value types and constraints

- Put validation and normalization in named `Annotated` value types using explicit
  `type Name = ...` aliases. Scalar declarations have one public home in `types.py`.
- Use `StringConstraints` for string length, pattern, whitespace, and case rules.
  Use `Field` for numeric and collection bounds and descriptive metadata; do not
  alternate between the two for string constraints.
- Reuse shared metadata such as `DATABASE_ID_CONSTRAINTS` and
  `COLLECTION_CONSTRAINTS`. Treat these objects as constants; never mutate them.
  Keep property defaults and aliases out of shared constraint objects.
- Models declare those types, requiredness, defaults, and field aliases.
- Use `Field()` on model properties for defaults, factories, aliases, or descriptions;
  define value bounds in the owning type instead of repeating them on properties.
- Keep union discriminators and stable schema titles on named union definitions.
- Reuse Pydantic's constraint primitives. Do not shadow their names with custom classes.
- Serialized survey answer bounds are data: models such as `TextAnswerBounds`
  describe authored rules and are distinct from Pydantic configuration.
- Prefer explicit scalar and structured value shapes over `Any`, arbitrary dictionaries,
  or recursive `JsonValue`. Use open JSON only when the contract actually requires it.
- Use bounded title/text types and explicit presentation/tone vocabularies.
- Use model validators for relationships that types cannot express, such as ordered bounds.
  Prefer discriminated models when one field selects a different valid object shape.
- Validate definitions with `SurveyDefinition` and answers with `AnswerData` or
  its request subclasses. Their Pydantic validators own specification/value
  consistency; do not repeat those checks in domain family-dispatch loops.
  Stored publication/access state and response-store availability remain domain
  guards. Answer validation alone does not prove published-field provenance.

## Identity and representation

- Keep semantic names: `SurveyVersionId`, `SurveyFieldUuid`, `ClientMutationId`,
  `UserId`, and `Auth0UserId` communicate distinct identities.
- Define each meaningful identity as a private `NewType` over its actual Python
  representation, then expose a public annotated alias. The private variable name
  must match the `NewType` name, for example `_ProjectId = NewType("_ProjectId", int)`.
  Public `ProjectId` uses that nominal identity and `DATABASE_ID_CONSTRAINTS`.
- Different identities remain distinct to Pyright even when their runtime values
  are integers or UUIDs. Constrained values such as titles do not need nominal wrappers.
- Parse external primitives with `TypeAdapter(Type).validate_python(...)` or
  `Model.model_validate(...)`; direct Pydantic constructors expect already typed
  identities to satisfy static checking. Never use casts to hide a boundary mismatch.
- Keep descriptive reference fields such as `survey_version_id`; use `id` for
  the identity of the object itself.
- Do not confuse a version identity, sequential version number, and document revision.
- Preserve opaque external identifiers; do not trim, lowercase, split, or otherwise
  transform them without an explicit boundary rule.
- An annotation does not validate an ordinary function argument or variable assignment.
  Validate external values at their actual ingress boundary.

## ORM mappings

- Use shared value types in `Mapped[...]` when the value is shared with application
  or API contracts, including foreign keys referencing those shared identities.
- Keep column storage types, nullability, foreign keys, defaults, constraints,
  relationships, and indexes unchanged during annotation-only consolidation.
- Do not add ORM validators, conversion hooks, or SQL constraints merely to reuse a type.
  Pydantic metadata does not automatically validate ORM assignments.
- `app/db/type_mapping.py` explicitly maps public identity aliases to SQL storage
  for both declarative bases. Keep SQL policy separate from Pydantic constraints.
- Storage-only hashes, encryption material, internal IDs, and configuration data
  need not acquire API-oriented types.
- JSONB containing a serialized document remains stored JSON, not an instance
  of a Pydantic model unless an explicit conversion layer exists.
- Survey definitions use `db/json_types.py:SurveyDefinitionJSONB` as that explicit
  boundary: typed models serialize to JSON on write and stored JSON becomes a
  `SurveyDefinition` on load. SQL storage remains JSONB; empty drafts may have
  no definition. There is no Pydantic validation on ordinary ORM assignment.
- `surveys_repo.get_definition` returns an independent document snapshot scoped
  to project, survey, and version number. `update_definition` replaces the whole
  document, marks it modified, and flushes without committing. Services own
  authorization, editability, revision policy, document identity, and field lookup.

## Typed ORM construction

All mapped classes use SQLAlchemy's native dataclass constructor generation.
Every model declares `kw_only=True` explicitly for consistent runtime and Pyright
behavior. Database-generated IDs/timestamps and relationships use `init=False`;
nullable fields use `default=None`; scalar defaults reflect their existing domain
and SQL defaults. Operation timestamps that callers supply remain constructor
inputs, with an aware UTC creation default where appropriate.

Do not add handwritten forwarding constructors or an unset sentinel. Neither
annotations nor dataclass construction add Pydantic validation to ORM assignments.
Tests must check every mapped class, actual creation sites, generated defaults,
relationship foreign keys, and unchanged PostgreSQL DDL.

## Requests, responses, and defaults

- Top-level request models and top-level union variants end in `Request`.
- Request-only models embedded inside another request use the `NestedModel` suffix.
  Shared domain models keep their domain names.
- `T | None` permits null; a default such as `= None` additionally permits omission.
- Default fixed response labels and genuinely optional embedded objects where appropriate.
- Recorded timestamps and factual results must come from their source. Do not generate
  `now()` as a fallback for persisted completion, creation, or save times.
- Permission collections use shared sets and serialize as JSON arrays; ordering is unspecified.
- Limit inputs and paginated outputs. Do not impose arbitrary collection caps on
  complete answer sets, event timelines, identities, or session histories.

## Global limits

- `limits.py` holds shared resource ceilings, pagination configuration, and storage bounds.
- Remove unused constants and redundant caps implied by a closed literal vocabulary.
- Define one-off business bounds once in their named value type; they do not each need
  a global constant. Self-explanatory minimums such as `ge=1` can live in the type.
- Preserve actual storage and product requirements. Do not merge different policies
  merely because their current numeric values happen to match.
- Align URL converters with the identities they carry. HTTP body limits remain
  separate from Pydantic validation after parsing.

## OpenAPI and verification

- Check runtime validation, generated JSON Schema, and downstream interpretation.
- Use explicit discriminators and stable titles for exported unions.
- Preserve requiredness, nullability, formats, aliases, uniqueness, and bounds.
- Publish declared constraints; do not invent limits from property or component names.
- Runtime validators may enforce relationships that JSON Schema does not fully express;
  do not claim schema generation alone proves equivalent enforcement.
- Include negative cases and round-trip checks when changing contracts. Verify ORM
  metadata is unchanged for annotation-only work.
- Naming affects frontend generation: the classifier recognizes `Request`/`In`
  and both `Response` and `Responses`; nested models are subtypes.
- Isolated schema checks do not establish application integration. The ongoing V2
  migration still has legacy runtime callers; full OpenAPI export and application
  checks must be completed when those consumers are migrated.
