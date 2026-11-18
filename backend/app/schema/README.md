# Schema conventions

These conventions apply when defining or changing value types across FlowForm.

## Ownership

- `models/` owns reusable data models and value types shared across application layers.
- `models/common/types.py` owns generic values and constraints: text, timestamps,
  counts, collection bounds, email addresses, and the underlying database identity range.
- Domain packages such as `models/projects/`, `models/survey/`,
  `models/identity/`, and `models/submission/` own semantic value types.
- `api/common/types.py` owns HTTP-specific values such as pagination, search,
  and request-only constraints. Promote a type into `models/` when other layers need it.
- `api/requests/` and `api/responses/` own operation contracts.
- `orm/` owns SQLAlchemy mappings. Shared models must not depend on API or ORM packages.
- `enums.py` owns enumerations shared across domains or persistence boundaries.

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

- Put validation and normalization in named `Annotated` value types.
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

## Identity and representation

- Keep semantic names: `SurveyVersionId`, `SurveyFieldUuid`, `ClientMutationId`,
  `UserId`, and `Auth0UserId` communicate distinct identities.
- Shared numeric identities reuse the underlying database range rather than
  redefining it. A semantic alias alone does not provide nominal type separation.
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
- Storage-only hashes, encryption material, internal IDs, and configuration data
  need not acquire API-oriented types.
- JSONB containing a serialized document remains stored JSON, not an instance
  of a Pydantic model unless an explicit conversion layer exists.

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
- Naming affects frontend generation: its current classifier recognizes `Request`/`In`
  and `Responses`; singular `Response` needs explicit consideration during generator work.
- Isolated schema checks do not establish application integration. The ongoing V2
  migration still has legacy runtime callers; full OpenAPI export and application
  checks must be completed when those consumers are migrated.
