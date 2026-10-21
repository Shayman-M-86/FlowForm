---
title: Survey builder and form-filler migration manifest
aliases: ["Survey builder and form-filler migration manifest"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-10-21
tags: [frontend]
related_code: []
related_docs:
  - "Engineering migrations"
  - "Survey document prototype overview"
---

# Survey builder and form-filler migration manifest

Prepared migration plan for importing the document-style survey builder and form
filler into FlowForm.

> Imported from `/home/shayman86/my-repos/Test-suite/FLOWFORM-MIGRATION.md` on
> 2026-10-21. The source wording is preserved apart from the page title and link
> formatting. This is prototype and migration material, not a description of
> completed FlowForm functionality. Source-relative paths and commands refer to
> the `Test-suite` checkout unless explicitly identified as FlowForm paths.
> Prototype source-file links are retained as code references. Validation results
> and dated implementation anchors below belong to the source snapshot; they
> were not rerun or refreshed for this import. FlowForm's backend document-model
> migration has since started, while the frontend integration remains unfinished.

Status: canonical planning handoff  
Last verified against both live checkouts: 2026-08-03

Source checkout:

```text
/home/shayman86/my-repos/Test-suite
```

Target checkout:

```text
/home/shayman86/my-repos/FlowForm
```

## Authority for future agents

Treat this document as the canonical truth for planning this migration.

- Do not rediscover the portability boundary from READMEs, design notes, or the
  old FlowForm builder before producing an implementation plan.
- Do not redesign the imported experience to resemble FlowForm's existing node
  builder. The external builder and filler are the intended visual direction.
- Use the file dispositions, target anchors, sequence, and decisions below as
  settled unless the user explicitly changes them.
- At implementation time, inspect the live source files named in this document
  to account for API drift. A wider documentation search is not a prerequisite.
- If this document and executable source ever conflict, executable source is
  final truth; update this manifest in the same change that resolves the drift.

This repository has already completed the preparation refactor. The remaining
work is a separate migration into FlowForm, not more prototype redesign.

## Prepared outcome

The source repository now has four explicit boundaries:

```text
host/demo shell
    -> public portable entry (src/index.ts)
        -> SurveyBuilder / FormFiller / top-bar elements
            -> narrow controller contracts
                -> contained temporary model
```

The portable side has no imports from `src/demo`. Theme choice, storage,
routing, API calls, fake project context, and data-inspection chrome all remain
outside the portable components.

The visual behavior remains intact:

- three-region desktop authoring layout;
- mobile outline drawer and inspector bottom sheet;
- selected-content and insertion interactions;
- continuous desktop filler;
- section-by-section mobile filler;
- optional 390-pixel phone preview frame;
- conditional visibility, validation, progress, and per-answer saving;
- host-supplied light/dark semantic tokens.

## Public API

The only supported source entry is `src/index.ts`. It exports:

- `SurveyBuilder` and `SurveyBuilderProps`;
- `FormFiller`, `FormFillerProps`, `FormFillerLayout`, and `MobileFrame`;
- `SurveyBuilderController` and `FormFillerController`;
- the temporary model and `SurveyAction` types needed by adapters;
- reusable top-bar elements;
- the small set of generic prototype primitives.

Nothing under `src/demo` is exported. Do not add demo exports to make a future
migration convenient.

The package currently exposes these source-level paths:

```json
{
  ".": "./src/index.ts",
  "./portable.css": "./src/styles/portable.css"
}
```

These exports describe the intended boundary. The migration should copy or
move source into `@flowform/builder`; it should not publish this prototype as a
standalone production dependency.

## Controller contracts

### SurveyBuilderController

Canonical definition: `src/contracts/surfaces.ts`.

```ts
interface SurveyBuilderController {
  survey: SurveyDefinition
  selection: { sectionId: string | null; blockId: string | null }
  collapsedSections: ReadonlySet<string>
  dispatch(action: SurveyAction): void
  selectBlock(sectionId: string, blockId: string): void
  selectSection(sectionId: string): void
  clearSelection(): void
  toggleSectionCollapsed(sectionId: string): void
}
```

The component does not know how edits are persisted, authorized, versioned, or
sent to an API. The current demo store only happens to satisfy this contract
structurally.

`SurveyBuilder` also accepts host-owned presentation inputs:

- `contextLabel` for optional project/survey context;
- controlled `outlineOpen` state for a host top-bar trigger;
- controlled or internal `settingsOpen` state.

### FormFillerController

```ts
interface FormFillerController {
  survey: SurveyDefinition
  response: SurveyResponse
  saveAnswer(fieldId: string, value: AnswerValue): void
  completeResponse(outcome?: string): void
  restartResponse?: () => void
  answerSavedAt: number | null
}
```

`restartResponse` is optional because a production submission session may not
allow restart. The host owns completion lifecycle, persistence, errors, and
network state.

`FormFiller` defaults to responsive layout. Explicit `desktop` and `mobile`
layouts exist for builder preview. `mobileFrame="device"` is preview chrome and
must not be used on the real respondent route. `completionDetails` is a
host-owned slot; the demo uses it for its data-inspector teaching text.

## Replaceable top bar

Do not migrate `src/demo/DemoTopBar.tsx`. It is only a
reference composition for the external prototype.

Migrate and compose the independent elements from
`src/components/topbar/BuilderTopBarElements.tsx`:

| Export | Responsibility | FlowForm placement |
| --- | --- | --- |
| `SurveyTitleControl` | Editable title and optional status badge | Builder-specific toolbar area |
| `SaveStatus` | Generic recent/idle/unavailable save signal | Beside FlowForm save/version controls |
| `HistoryActions` | Undo and redo buttons | Builder toolbar when real history exists |
| `BuilderPreviewSwitch` | Builder/preview mode selection | Builder toolbar or route-level controls |
| `PreviewDeviceSwitch` | Desktop/mobile preview selection | Visible only while previewing |

The elements take ordinary values and callbacks, not a demo store. FlowForm can
place them in its existing chrome without accepting the prototype header.

The best current target is
`frontend/apps/studio-app/src/components/SurveyBuilderTabChrome.tsx`, especially
`SurveyBuilderVersionToolbar`. The global
`frontend/apps/studio-app/src/components/SiteHeader.tsx` should remain app-owned
unless FlowForm first adds an explicit route-toolbar slot.

## Styling contract

### What moves

`src/styles/portable.css` contains:

- semantic Tailwind mappings;
- the centralized authoring/content type scale;
- radius, border, control-height, icon, layout, and device-frame geometry;
- shared border/divider/input/overlay/scroll/animation utilities;
- only `.ff-surface`-scoped element behavior;
- responsive builder grid rules;
- reduced-motion behavior scoped beneath `.ff-surface`.

It deliberately does not choose light or dark mode.

### What does not move

`src/styles/demo-theme.css` supplies the external
prototype's warm palette. `src/styles/demo-shell.css`
owns `html` and `body`. `src/index.css` combines Tailwind and
the demo layers. All three are prototype-owned and must remain behind.

### Semantic token mapping

| Portable role | FlowForm token |
| --- | --- |
| `background` | `--background` |
| `sidebar` | `--sidebar` |
| `card` / `card-foreground` | `--card` / `--card-foreground` |
| `popover` / `popover-foreground` | `--popover` / `--popover-foreground` |
| `foreground` | `--foreground` |
| `soft-foreground` | `--soft-foreground` |
| `muted` / `muted-foreground` | `--muted` / `--muted-foreground` |
| `primary` | `--primary` |
| `primary-saturated` | `--primary-saturated` |
| `primary-foreground` | `--primary-foreground` |
| `secondary` | `--secondary` |
| `accent` / `accent-muted` | `--accent` / `--accent-muted` |
| `border` | `--border` |
| `input` | `--input` |
| `ring` | `--ring` |
| `destructive` | `--destructive` |
| `success` | `--success` |
| `warning` | `--warning` |
| radii | `--radius` and derived Tailwind radii |
| shadows | `--app-shadow-xs`, `--app-shadow-sm`, `--app-shadow-lg` |

The source has verified support for `.dark`, `data-theme="light"`, and
`data-theme="dark"`. Portable React components contain no theme state and do
not write to `document.documentElement`.

### FlowForm style anchors

At implementation time inspect only these first:

```text
frontend/packages/styles/src/tokens.css
frontend/packages/styles/src/components.css
frontend/packages/styles/package.json
```

FlowForm already exports `@flowform/styles`, `@flowform/styles/tokens.css`, and
`@flowform/styles/components.css`. Import FlowForm's style package once at the
host level. Move only the `ff-*` component roles FlowForm does not already
provide. Do not copy the demo palette or create another `ThemeProvider`.

## Shared primitive mapping

Carry the local primitives initially to preserve behavior, then replace them
one at a time. Do not rewrite purpose-built survey controls merely to use a
generic package component.

| Source primitive | FlowForm candidate | Decision |
| --- | --- | --- |
| `Button` | `@flowform/ui` `Button` | Replace early; variants and sizes align closely |
| `IconButton` | `Button` with icon/ghost treatment | Replace after confirming accessible labels and exact hit areas |
| `Field` + `ff-input` | `Input`, form-field helpers | Replace generic inspector fields |
| `Toggle` | `@flowform/ui` `Toggle` | Replace directly after prop adapter |
| `Badge` | `@flowform/ui` `Badge` | Replace directly after variant mapping |
| `SegmentedControl` | `ButtonGroup` or `TabSelector` | Choose by semantics, not appearance alone |
| `BottomSheet` / `SlideOver` | `Modal` only if behavior matches | Retain until focus trap and mobile geometry reach parity |
| `AutoTextarea` | `ExpandableTextArea` where compatible | Verify inline document editing before replacement |
| `AnswerControl` | none | Keep purpose-built |
| `RenderedBlock` | none | Keep purpose-built |
| builder canvas/block/insert controls | none | Keep purpose-built |

Current FlowForm UI anchors:

```text
frontend/packages/ui/src/index.tsx
frontend/packages/ui/src/components/ui/Button.tsx
frontend/packages/ui/src/components/ui/Input.tsx
frontend/packages/ui/src/lib/sizes.ts
frontend/packages/ui/src/lib/formFieldStyles.ts
```

`@flowform/ui` already supports `xxs` through `xl`, both `danger` and
`destructive`, and the core components listed in the original preparation
brief.

## Complete file disposition

### Move: public surfaces and feature internals

| Source file | Role in FlowForm |
| --- | --- |
| `src/index.ts` | Template for additions to `@flowform/builder` public exports |
| `src/builder/index.ts` | Builder feature entry |
| `src/builder/SurveyBuilder.tsx` | Responsive builder composition |
| `src/components/builder/AddContentMenu.tsx` | Portable content catalogue menu |
| `src/components/builder/Canvas.tsx` | Document canvas and section composition |
| `src/components/builder/CanvasBlock.tsx` | Inline block editing and specialized previews |
| `src/components/builder/InsertPoint.tsx` | Between-content insertion interaction |
| `src/components/builder/Outline.tsx` | Navigation and keyboard-accessible reordering |
| `src/components/inspector/Inspector.tsx` | Inspector composition and tab shell |
| `src/components/inspector/ContentPanel.tsx` | Content editing fields |
| `src/components/inspector/AnswerPanel.tsx` | Interaction and response configuration |
| `src/components/inspector/BehaviourPanel.tsx` | Visibility and validation configuration |
| `src/filler/index.ts` | Filler feature entry |
| `src/filler/FormFiller.tsx` | Desktop/mobile respondent orchestration |
| `src/filler/RenderedBlock.tsx` | Respondent content rendering |
| `src/filler/AnswerControl.tsx` | Purpose-built response controls |
| `src/components/topbar/BuilderTopBarElements.tsx` | Host-composable toolbar pieces |

### Move initially: shared implementation support

| Source file | Role and later treatment |
| --- | --- |
| `src/components/shared/ui.tsx` | Temporary generic primitives; replace incrementally with `@flowform/ui` |
| `src/components/shared/utils.ts` | `cx` and canonical input role; map `cx` to FlowForm `cn` later |
| `src/components/shared/hooks.ts` | Dismissal and recent-save behavior |
| `src/components/shared/ContextualToolbar.tsx` | Builder-specific selected-content toolbar |
| `src/components/shared/Overlay.tsx` | Responsive sheet/drawer with focus management |
| `src/styles/portable.css` | Scoped styles and semantic mappings only |
| `src/utils/ids.ts` | Temporary client identifiers used by authoring |
| `src/utils/validation.ts` | Temporary filler validation behavior |

### Move temporarily: model boundary to adapt or replace

| Source file | Purpose |
| --- | --- |
| `src/contracts/surfaces.ts` | Narrow visual controller boundary |
| `src/contracts/survey-actions.ts` | Temporary authoring command union |
| `src/model/survey.ts` | Temporary document-shaped survey definition |
| `src/model/response.ts` | Temporary field-shaped response and answer revision logic |
| `src/model/conditions.ts` | Conditional visibility evaluation |
| `src/model/contentCatalogue.ts` | Supported content types and factories |

Do not merge these types into visual component files. Do not prematurely force
them into FlowForm's existing `SurveyNode` model. The target model is expected
to evolve toward generated frontend contracts.

### Leave behind: prototype application

| Source file | Why it stays |
| --- | --- |
| `src/App.tsx` | Vite demo compatibility shim |
| `src/main.tsx` | Standalone demo bootstrap |
| `src/index.css` | Demo stylesheet aggregator |
| `src/styles/demo-theme.css` | Prototype palette values |
| `src/styles/demo-shell.css` | Global demo `html`/`body` ownership |
| `src/demo/DemoApp.tsx` | Prototype mode routing and shell composition |
| `src/demo/DemoTopBar.tsx` | Replaceable prototype header, logo, breadcrumb, and Data action |
| `src/demo/DataInspector.tsx` | Prototype-only data teaching drawer |
| `src/demo/demoSurvey.ts` | Seeded mock survey |
| `src/demo/useDemoStore.ts` | Local in-memory/browser demo orchestration |
| `src/demo/useLocalStorage.ts` | Prototype persistence and storage keys |
| `src/demo/surveyReducer.ts` | Prototype implementation of temporary authoring actions |

Also leave the external-repository tooling and assets behind:

```text
index.html
public/favicon.svg
vite.config.ts
tsconfig.json
tsconfig.app.json
tsconfig.node.json
.oxlintrc.json
package-lock.json
```

Merge dependency and export requirements into FlowForm's workspace packages;
do not copy the prototype `package.json` wholesale.

## Current FlowForm implementation anchors

These were verified in the live target checkout on 2026-08-03:

```text
frontend/packages/builder/package.json
frontend/packages/builder/src/index.ts
frontend/packages/builder/src/pages/builder/NodePage.tsx
frontend/packages/builder/src/components/form_filler/FormFiller.tsx

frontend/apps/studio-app/src/pages/SurveyWorkspaceTabPages/SurveyBuilderTab.tsx
frontend/apps/studio-app/src/pages/SurveyWorkspaceTabPages/useSurveyBuilderController.ts
frontend/apps/studio-app/src/components/SurveyBuilderTabChrome.tsx
frontend/apps/studio-app/src/pages/RespondPage.tsx
frontend/apps/studio-app/src/components/SiteHeader.tsx
frontend/apps/studio-app/src/api/generated/schema.ts
```

The current builder package exports `NodePage`, the old `FormFiller`, node
types, draft storage, and preview storage. The Studio builder tab owns version
loading, permissions, save/publish/archive lifecycle, dirty-state switching,
AI import, and toasts. `RespondPage` owns link resolution, authentication,
submission-session creation/resume, answer PUTs, and final completion.

Preserve those application responsibilities. Replace the visual surfaces
behind adapters; do not move API/session logic into `SurveyBuilder` or
`FormFiller`.

## Required migration sequence

1. **Create a side-by-side namespace.** Copy portable code into a clearly
   temporary subtree such as `frontend/packages/builder/src/portable/`. Avoid
   colliding with the current `FormFiller` export until adapters compile.
2. **Wire styles.** Confirm the Studio and respondent hosts import
   `@flowform/styles`. Add the scoped `ff-*` rules to the builder package and
   remove semantic mappings already supplied by FlowForm. Never import
   `demo-theme.css` or `demo-shell.css`.
3. **Make public exports.** Add `SurveyBuilder`, the new filler under a
   non-colliding temporary name if necessary, controller types, and top-bar
   elements to `frontend/packages/builder/src/index.ts`.
4. **Carry generic primitives for parity.** Keep local primitives until the
   pages render correctly. Replace them with `@flowform/ui` in small,
   independently verified changes.
5. **Build a builder adapter.** Adapt the real Studio controller/version state
   to `SurveyBuilderController`. Keep permissions, dirty state, version
   switching, save/publish/archive, and AI import in Studio. Do not make
   `SurveyBuilder` fetch data.
6. **Compose toolbar elements.** Insert only the useful extracted controls into
   `SurveyBuilderVersionToolbar` or an explicit route-toolbar slot. Do not copy
   `DemoTopBar`.
7. **Build a respondent adapter.** Keep `RespondPage` network and authentication
   lifecycle. Map loaded survey data into the temporary definition at one
   adapter boundary, and map `saveAnswer`/`completeResponse` back to the
   existing submission-session API.
8. **Run old and new surfaces side by side.** Use a development-only switch or
   isolated route while validating behavior. Do not delete `NodePage` or the
   old filler before parity and contract decisions are complete.
9. **Resolve the final model once.** When generated contracts for the new model
   are final, replace the temporary model and action adapters in one bounded
   layer. Keep the visual props/controllers stable where possible.
10. **Remove superseded code.** Only after builder, preview, public respondent,
    authenticated respondent, save/publish, and mobile behavior all pass.

## Decisions that must remain intact

- The new design replaces or significantly reshapes the current FlowForm
  builder; it is not a skin for `NodePage`.
- Definition editing and response answering remain separate state systems.
- Choice answers store stable option IDs, never labels.
- Conditional visibility only references earlier questions in the temporary
  model, keeping conditions acyclic by construction.
- Hidden answers are retained but excluded from validation and progress.
- Desktop and mobile fillers render the same blocks; only sequencing differs.
- The real respondent page must not render the optional phone bezel.
- The host owns theme, routing, permissions, project context, persistence, API
  errors, and server lifecycle.
- Generic primitives may be replaced. Specialized survey interactions must be
  preserved unless parity is demonstrated.
- No broad `html`, `body`, `button`, `input`, or universal reset may move into
  the portable builder package.

## Known implementation-time decisions

These are intentionally deferred; they are not reasons to repeat discovery:

1. Final mapping between the temporary document model and FlowForm's future
   generated schema.
2. Whether undo/redo is implemented in the real builder controller before the
   `HistoryActions` element is shown.
3. How server-side save errors and pending states extend the filler controller.
4. Whether FlowForm's `Modal` can exactly replace the mobile sheet/drawer focus
   and geometry behavior.
5. Whether builder preview is a mode within the Studio tab or a dedicated
   route. The visual `BuilderPreviewSwitch` supports either host decision.
6. Which existing old-builder exports remain during the transition.

## Verification baseline

The prepared source currently passes:

```bash
npm run build
npm run lint
```

Lint completes with no warnings.

A real Chromium render pass completed 21 of 21 checks with zero runtime or
console errors. It covered:

- desktop builder, outline, and inspector;
- resolved 32-pixel display typography token;
- semantic color tokens;
- extracted mode control;
- desktop filler and conditional-question behavior;
- mobile filler sequencing and exact 390-pixel preview frame;
- `data-theme="dark"` and `.dark` equivalence;
- narrow builder without docked side panels;
- outline dialog and settings bottom sheet;
- demo data inspector.

The source audit also confirms:

- no portable import reaches `src/demo`;
- no arbitrary typography, line-height, tracking, radius, shadow, border-width,
  or layout Tailwind values remain in TSX;
- the only raw `border-0` is the semantic reset on a filler `fieldset`;
- component colors use semantic utility roles rather than prototype palette
  names or inline color values.

## FlowForm acceptance gates

Do not declare the later migration complete until all of these hold:

- `SurveyBuilder` renders inside the Studio builder route with FlowForm theme
  tokens in both themes;
- version, permission, dirty-state, save, publish, archive, and AI-import flows
  remain owned and functional in Studio;
- extracted top-bar elements compose into FlowForm chrome without importing the
  prototype header;
- the real respondent route preserves resolve/resume/save/complete semantics;
- mobile filler uses the section-by-section experience without a device frame;
- responsive outline and settings surfaces retain keyboard focus behavior;
- generic primitive replacements have visual and interaction parity;
- no demo file, local-storage key, fake project context, seeded survey, or demo
  data inspector enters the FlowForm package;
- FlowForm's standard frontend build, lint, typecheck, and relevant tests pass;
- rendered light/dark desktop/mobile QA has no console errors.

When implementation starts, begin with the files in **Current FlowForm
implementation anchors** and this manifest. No broader planning-document search
is required.

## Related documents

- [[migrations-index|Engineering migrations]]
- [[survey-document-prototype-overview|Survey document prototype overview]]
