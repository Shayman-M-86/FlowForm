---
title: Documentation restructure plan (tree + graph)
aliases:
  - "Documentation restructure plan (tree + graph)"
document_type: plan
status: draft
authority: canonical
verified_against_commit: null
tags: [meta, tooling]
related_code:
  - "../../../scripts/docs/"
  - "../../../.claude/hooks/"
related_docs:
  - "../../00-overview/documentation-model.md"
---

# Documentation restructure plan (tree + graph)

Adapt the proposed **tree-shaped repository with graph-like cross-links** model
to FlowForm's existing `docsys` tooling, keeping everything the current system
already does well and changing only what the new structure genuinely requires.

## Decisions locked in

- **Folder naming:** drop numeric prefixes; move to semantic names under two
  collections (`project-knowledge/`, `engineering-workspace/`).
- **Vocabulary:** keep the existing split — `status` = lifecycle
  (`scaffold|draft|verified`), `authority` = canonical/etc. — and **extend
  additively**. Do *not* fold the proposal's `canonical/deprecated/archived`
  into `status`. Add new `document_type` and `tag` values only as real docs
  need them.
- **Identity:** keep **title-as-identity** (no `id` field). The proposal's
  "preserve the ID on move" guarantee is already provided by stable, unique
  titles, which the validator enforces. This is a deliberate simplification of
  the proposal.

## What is kept unchanged (do not rebuild)

The proposal is written as if starting from plain Markdown. These already exist
and must survive the restructure untouched at the behaviour level:

- **Index / document model** — `scripts/docs/docsys/model.py`, `index.py`
  emitting `docs/90-generated/documentation-index.json` (= the proposal's
  "internal document record" + "derived graph").
- **Code↔doc linkage + impact** — `related_code` / `change_triggers` /
  `exclusions` glob resolution and `impact.py`.
- **Freshness / staleness** — `freshness.py`, keyed on
  `verified_against_commit`.
- **Live automation** — the MCP server (`docsys/mcp_server.py`) and the
  `.claude/hooks/` doc-impact + doc-review hooks.
- **Obsidian flavour** — `[[wiki links]]`, title-matching `aliases`. Links
  resolve by title/stem, so they survive path changes for free.

These operate on **titles** and **`related_code`**, both of which are invariant
under the move. No changes needed to the hooks, MCP server, impact, or
freshness engines.

## Conflicts the restructure must resolve

| Proposal says | Current reality | Resolution |
|---|---|---|
| Stable `id` field | Title = identity | Drop `id`; enforce title stability (already validated) |
| `related:` by id | `related_docs:` by title | Keep `related_docs`; wording only |
| `status` absorbs canonical/etc. | `status` + separate `authority` | Keep split (locked decision) |
| Every folder has `index.md` | No folder-head concept; `rglob("*.md")` | **New**: recognise + require `index.md` |
| `parent`/`children` from tree | Not derived | **New**: derive from filesystem |
| Backlinks/tag/type indexes generated | Only impact/freshness/health generated | **New**: backlink + facet generators |

## Path-coupling audit (what breaks on the move)

Tooling is mostly path-agnostic. The only hardcoded assumptions found:

- `model.py` — `GENERATED_DIR = docs/90-generated`, and `is_generated` prefix
  check. **Keep `90-generated`'s role** (generated outputs) but it can be
  renamed to `reference/generated/` per the proposal; update these two
  constants if so.
- `context.py` — heuristic that treats `30-workflows` docs specially. Rekey to
  the new workflow location (or to `document_type == "workflow"`, which is more
  robust than a path).
- `generate-repository-tree.py` — writes to `90-generated/`, links to
  `60-reference/…` and `90-generated/…` by stem. Update output path + wiki
  targets.
- Numerous doc bodies + `related_docs` reference
  `docs/00-overview/documentation-model.md`. Because links resolve by
  **stem/title**, wiki links survive; only **relative Markdown links** in
  bodies and `related_code`/`related_docs` written as **relative paths** need
  rewriting. A link-rewrite pass handles this mechanically.

The governing conventions doc is `docs/00-overview/documentation-model.md` — it
must be updated *first* since the validators are "the executable form of those
rules".

---

## Staged migration

Mirrors the proposal's §14 but sequenced to keep the tree valid and CI green at
every stage.

### Stage 0 — Freeze conventions (governing doc)

- Update `documentation-model.md` to describe: two collections, `index.md`
  folder heads, single-parent-from-filesystem, title-as-identity, file→folder
  promotion, the additive vocabulary policy.
- This doc is the source the validators encode; changing it first prevents the
  validators and the docs from disagreeing mid-migration.

### Stage 1 — Tooling: understand `index.md` + parent/child (no content moved yet)

Build against the **current** tree so it's testable before churn.

1. `model.py`
   - Mark each `index.md` as its folder's head; add `Document.is_folder_head`.
   - Derive `parent_rel` (nearest ancestor `index.md`, or collection root) and
     `children` (docs whose parent is this head).
   - Add these to `DocSet`.
2. `validate.py` + standalone `validate-doc-metadata.py` (keep the two in sync —
   the standalone one is the CI gate):
   - Every directory containing Markdown has an `index.md`.
   - Optional `parent:` field must match the inferred parent (fail on conflict).
   - No document lists itself in `related_docs`.
   - (Existing checks — required keys, unique titles, alias-matches-title, tag
     vocab, status vocab, `related_docs` resolves — stay as-is.)
3. `index.py` — emit `parent`, `children`, and `collection`
   (`project-knowledge` | `engineering-workspace`) per entry (§12 fields).

Acceptance: `python3 -m docsys index` + validators pass on the *current* tree,
with new fields populated and (initially) `index.md`-missing warnings listing
every folder that will need a head.

### Stage 2 — Introduce collections + folder heads (content move)

- Create `docs/project-knowledge/` and `docs/engineering-workspace/`.
- Move existing docs to their single structural parent:
  - `10-architecture`, `20-domains`, `40-implementation` → spread across
    `project-knowledge/{backend,frontend,data,security,infrastructure,...}`.
  - `50-decisions` → `engineering-workspace/decisions/`.
  - `70-planning/{active,future,completed}` → `engineering-workspace/planning/…`.
  - `30-workflows` → nearest subsystem, or a workflows area; update
    `context.py`'s heuristic.
- Add `index.md` to **every** folder (define subject, scope, model, children
  intro, cross-links — not just a file list).
- Keep titles identical across every move (identity invariant).
- Run a link-rewrite pass for relative Markdown links + relative
  `related_code`/`related_docs` paths. Wiki links need no change.
- `90-generated/` → `project-knowledge/reference/generated/`; update `model.py`
  constants and `generate-repository-tree.py`.

Acceptance: validators + index build clean; `git log --follow` works on moved
files (use `git mv`); no broken links reported.

### Stage 3 — Metadata pass (additive)

- Add any new `document_type` values the new structure needs (e.g. `overview`
  for `index.md` heads) — extend the vocab, don't replace it.
- Fill `related_code` / `related_docs` where the move surfaced gaps.
- Leave `status`/`authority` semantics exactly as they are.

### Stage 4 — Generated discovery outputs

- New generators writing **only** into `reference/generated/` (bounded, never
  into authored Markdown):
  - Backlinks (reverse of `related_docs`/wiki links) — authors never hand-maintain these.
  - Tag index, document-type index, code-to-document index.
  - Orphan report (already partpossible via health), Mermaid tree view.
- Impact / freshness / health generators keep their current outputs.

Acceptance: outputs regenerate deterministically; a `--check` mode fails CI if
regeneration would change committed output.

---

## Explicitly out of scope / rejected from the proposal

- **`id` field** — rejected; title-as-identity already delivers the guarantee.
- **Folding `authority` into `status`** — rejected; keeps validator + all
  existing frontmatter working.
- **Big up-front `document_type` list** — deferred; add types as docs appear.
- **Empty speculative folders** — not created; a folder appears only with real
  content (proposal rule 5, adopted).

## Open questions

1. Rename `90-generated` → `reference/generated`, or keep the name for lower
   churn? (Plan assumes rename per proposal; trivial to keep.)
2. `30-workflows`: dissolve into subsystems, or a dedicated
   `engineering-practices/` workflows area? Affects the `context.py` rekey.
3. Do we want a lightweight optional `parent:` field at all, given it must
   always equal the inferred parent? (Validation-only value: catches misfiled
   docs.)
