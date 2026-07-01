# Survey Versioning & Publishing

## Why Not Just a Status Flag

A survey being "published" isn't a boolean toggle on one row. Studio needs to
keep editing a survey after it's live without touching what respondents are
currently seeing, and it needs a defensible answer to "what did this survey
actually look like when this response was submitted?" That requires the draft
being edited and the version respondents hit to be genuinely different rows,
not the same row with a flag flipped.

---

## Versions Are Rows, Not States

Each survey can have multiple `survey_versions` rows, each with its own
`version_number` (sequential per survey, `max + 1` on creation), its own
question/rule tree, and its own `status`: `draft`, `published`, or `archived`.

The survey itself tracks `published_version_id` — a pointer to whichever
version row is currently live. Respondents always resolve through this
pointer; Studio's builder always operates on a `draft` row. These are
never the same row.

---

## The Publish Transition

Publishing (`services/surveys.py` → `publish_version`) is gated by two rules
in `domain/version_rules.py`:

- `ensure_is_draft()` — only a `draft` version can be published.
- `ensure_has_questions()` — the version must have at least one question node.
  An empty draft cannot go live.

On success, the repository layer does three things in one flush sequence:

1. If a different version was previously published, detach it from the survey
   (`published_version_id = None`, flush) and mark that old version
   `archived`.
2. Mark the new version `published`, set `compiled_schema` and `published_at`.
3. Point `survey.published_version_id` at the new version.

The old published version isn't deleted — it becomes `archived`, an
immutable historical record. There's no un-archiving path; a previous version
can only become live again by being copied into a fresh draft and re-published
through the normal flow.

---

## The Compiled Schema

At publish time, the service walks the version's live question tree and
scoring rules and materializes them into a single `compiled_schema` JSONB
blob (node id, type, sort key, content; scoring key and schema per rule).
This is what the public site actually reads at submission time — not a live
join across normalized tables.

This matters for the "what did the respondent actually see" question: the
compiled schema is a snapshot taken at the moment of publish, not a live
view. Editing the draft afterward cannot retroactively change what a past
respondent's session was validated against, because the published version's
`compiled_schema` isn't touched by draft edits.

---

## Draft Editability Is Enforced, Not Assumed

Every content mutation — creating, updating, or deleting a question node or
scoring rule — routes through `version_rules.ensure_is_editable(version)`,
which is a one-line check: `status != "draft"` raises
`VersionNotEditableError`. This is called from `services/content.py` on every
mutating path, not just the entry point to the builder. There's no separate
"lock" state; a version's own status *is* the lock.

---

## Copying Forward

To edit a published survey, Studio doesn't unlock the published version — it
creates a new draft and clones into it (`copy_version_to_draft`):

1. Create a new version row via `create_version` (next sequential number).
2. Clone question nodes from the source version.
3. Clone scoring rules from the source version.

The source version can be `published` or `archived` — cloning doesn't care
about status, only the *destination* draft's editability is enforced going
forward.

---

## Summary

| Concept | Representation |
|---|---|
| "Live" survey | `survey.published_version_id` → one `survey_versions` row |
| Editable draft | A version row with `status = "draft"` |
| Historical version | A version row with `status = "archived"`, never deleted |
| What respondents see | `compiled_schema` snapshot taken at publish time, not live tables |
| Edit lock | `version.status != "draft"` checked on every content mutation |

---

## Loose Threads

**No rollback.** Only the most recently published version can be active.
Reverting to a previous published version means copying that old version
forward into a new draft and publishing it again — there's no "repoint
`published_version_id` at an older archived version" shortcut, and doing so
manually would bypass the archive invariant.

**`deleted_at` exists but is unused.** The `survey_versions` schema has a
`deleted_at` column, but archiving — not soft-deletion — is the only
lifecycle transition actually implemented. The column appears to be vestigial
or reserved for a future path.

**Compiled schema immutability is convention, not enforcement.** Nothing at
the DB or service layer prevents a future code path from mutating
`compiled_schema` on an already-published version. The guarantee that
published snapshots are frozen depends on no code ever doing that, not on a
constraint that would stop it.
