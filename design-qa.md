# Homepage design QA

final result: passed

## Scope and visual target

Adaptation of the user-supplied marketing illustration and copy, rather than a
pixel-for-pixel clone. Preserve FlowForm's actual brand, builder, recordings,
animated icons, and light/dark themes. Planned automation must remain distinct
from current capabilities.

- Source: `/mnt/c/Users/Shayman/AppData/Local/Temp/codex-clipboard-f8c1364b-51da-472f-ae69-4fa4ff3554b2.png`
- Source dimensions: 1024 × 1536 pixels.
- Browser URL: `http://localhost:4321/`.
- Comparison: `/tmp/flowform-homepage-qa/reference-comparison.png`, source and
  implementation rendered together, each at 1024 × 1536, device scale 1.
- Additional browser captures: `/tmp/flowform-homepage-qa/1440-light-final.png`,
  `1024-light-final.png`, `390-light-final.png`, `1440-dark-final.png`.
- Focused captures: `studio-final.png`, `security-final.png`, `roadmap-final.png`
  under the same screenshot directory.
- Dark workspace-section evidence: `/tmp/flowform-homepage-qa/studio-dark-final.png`;
  its background matches the main dark page; light-mode muted background retained.
- Final builder-boundary evidence: `/tmp/flowform-homepage-qa/builder-boundary-fixed.png`.

## Comparison and fixes

1. Initial hero was too dense, with competing paragraphs and oversized example
   cards. Shortened the hero, tightened the form controls, and restored breathing
   room below the CTA. Re-captured desktop, tablet, mobile, and dark states.
2. User requested preservation of animated icons. Restored fourteen instances
   using existing assets, alongside all five original question recordings.
3. Focused captures exposed blank icons after viewport resizing: the old resize
   handler drew an animation image whose source was not yet loaded. Redraw the
   loaded still frame instead. Pixel checks verify painted frames after resizing.
4. A constrained builder viewport introduced nested scrolling. Removed the
   wrapper following user feedback; the builder grows with document flow.
5. The builder's oversized decorative canvas then painted into the next section.
   Clip the builder section with `overflow: clip`; this contains decoration
   without creating another scrolling container. Live browser wheel checks and
   the final dark screenshot confirm the boundary and document scrolling.

## Required visual surfaces

- Typography: existing Geist and FlowForm type tokens retained; handwritten
  annotations use self-hosted Caveat. Headings and controls wrap at checked widths.
- Layout: split hero, real branching example, handwritten callouts, live builder,
  recording carousel, workspace, trust, planned automation, use cases, and CTA.
  No document horizontal overflow at 390, 1024, or 1440 pixels.
- Colors: existing theme tokens retained; marketing accent text mixes primary
  with foreground. Both light and dark states inspected.
- Assets: supplied logo, original animated icons, and original recordings reused.
  Native interactive form controls illustrate branching; no fictional Studio
  screenshot, upload feature, analytics interface, or decorative replacement art.
- Content: benefit-led copy replaces schema/database/API terminology. Planned
  progression, reminders, and follow-ups carry explicit planned labels.

## Interaction verification

- All three hero choices reveal their respective follow-up field.
- Fresh browser storage receives the editable three-node adaptive starter.
- Existing empty and nonempty drafts are preserved.
- Working-professional answer reveals the numeric follow-up in the actual
  builder preview; submitting and returning to the builder works.
- Four viewport/theme runs completed without page errors.
- Fourteen animated icon instances initialize; hover playback and resize frames
  checked. All local anchor targets resolve.
- Normal document wheel scrolling over the builder verified; no inner builder
  scroll container. Decorative dots stop before the next section.

## Intentional differences and limits

The source's leaf logo, decorative colored backdrop, sidebar builder, and
unsupported upload/analytics controls are not reproduced. This pass uses the
existing brand and actual builder as requested. Hero spacing accommodates the
real controls and beta disclosure. The illustration is an interactive local
example; it does not publish surveys or transfer drafts into Studio.

Backend deployment and production authentication were not part of this pass.
Repo-wide documentation validators still flag existing abandoned review files;
the edited frontend documentation reports no metadata or link errors.
