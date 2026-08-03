---
title: Study interaction product direction
aliases: ["Study interaction product direction"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-08-04
tags: []
related_code: []
related_docs:
  - "Engineering ideas"
  - "Product knowledge"
  - "Builder and rules"
  - "Respondent access and continuity"
  - "Market and commercial hypotheses"
---

# Study interaction product direction

This note preserves a candidate product vision. It is not an accepted product
contract, roadmap, or description of implemented capability. Current behaviour
remains in [[product-index|Product knowledge]] and the implementation itself.

## Candidate vision

> FlowForm is an opinionated study interaction platform that simplifies
> participant-facing workflows through surveys and lightweight automation,
> while fitting into the broader research process instead of trying to replace
> it.

The important boundary is narrower than “participant lifecycle management.” A
participant's journey continues through recruitment, conversations, consent,
appointments, interventions, follow-up, and analysis. FlowForm would own the
structured interactions that pass through it, not the entire journey.

“Participant workflow platform” remains useful shorthand because FlowForm would
coordinate progression across stages. Used without qualification, however, it
can imply that the whole research workflow lives inside FlowForm. The current
working preference is therefore “study interaction platform,” or the fuller
description:

> FlowForm manages participant interactions and survey-driven automation within
> a study while fitting into the broader research workflow rather than replacing
> it.

This is also the distinction from trying to become a complete research
management platform or Electronic Data Capture system. FlowForm would provide a
focused operational layer and coexist with those systems where a study uses
them.

```text
recruitment
    |
    v
screening survey ---------> researcher review
    ^                              |
    |                              v
consent survey <------------ human decision
    |
    v
repeated survey ----------> notification / handoff
    ^                              |
    |                              v
follow-up survey <---------- work outside FlowForm
```

Participants may leave and return to FlowForm many times. The product acts as a
checkpoint and interaction engine inside a study rather than the continuous
manager of every participant activity.

## Proposed responsibility boundary

FlowForm would concentrate on:

- participant discovery and recruitment interactions;
- screening and explicit eligibility rules;
- consent interactions and recording progression evidence;
- asking people for structured information;
- distributing one-off and repeated surveys;
- tracking progress through survey-related milestones;
- evaluating simple, survey-derived operational rules;
- sending reminders, notifications, and other bounded actions; and
- surfacing participant status and exceptions that need researcher attention.

The research team would remain responsible for decisions and work that depend
on wider context, professional judgement, or systems outside FlowForm. Examples
include contextual eligibility, enrolment, or withdrawal decisions; calls and
appointments; diagnoses; treatment; emergency response; lab work; and
statistical interpretation. FlowForm may evaluate a declared eligibility rule
or record that a researcher approved a gate without becoming the source of the
researcher's professional judgement.

This creates a concise handoff:

```text
FlowForm owns participant interactions.
Researchers own participant decisions.
```

The wording is a design hypothesis, not a claim that every proposed interaction
or automation already exists.

## Automation boundary

Automation should reduce repetitive operational work and then stop at an
explicit handoff when human judgement is required.

```text
survey response
      |
simple rule evaluation
      |
bounded action or notification
      |
human judgement when context is required
```

Good candidates include sending a survey or reminder, checking a defined score
threshold, notifying a researcher, or progressing a survey-related milestone.
FlowForm should not autonomously diagnose, choose treatment, remove someone
from a study, reschedule an appointment, or contact emergency services. A
high-risk response may cause FlowForm to surface information promptly, but the
subsequent decision belongs to an accountable person and their established
process.

## Opinionated product shape

The product could make common journeys easy to start through templates such as
an anonymous survey, public recruitment, invitation-only participation,
screening and enrolment, or longitudinal follow-up. A template would create a
customisable survey-interaction flow; it would not imply that the whole study
workflow lives in FlowForm.

```text
create study
     |
choose operational template
     |
generate participant flow
     |
customise
     |
launch
```

The generated flow could provide an editable sequence such as:

```text
recruitment --> screening --> eligibility --> consent
    --> baseline --> follow-up --> complete
```

These would be operational templates shared across research methodologies, not
scientific classifications.

## Progression and gates

FlowForm should model events that are meaningful to participant progression,
not every activity surrounding them. Each stage can be understood as a gate:
what must be true before this participant may move forward?

Examples of gate evidence include:

- screening survey completed;
- explicit eligibility rule satisfied or researcher approval recorded;
- consent recorded; and
- baseline or follow-up survey completed.

FlowForm would care that the gate is satisfied. It would not need to model the
phone-call booking, staff availability, calendar conflict, interview duration,
lab appointment, or other external work that helped the study reach that state.
“Gate” may remain an internal model even if the interface uses more natural
research language.

The design target is the common “80% workflow”: recruit, screen, consent,
survey, and follow up. FlowForm should prefer a clear path through this common
shape over unlimited modelling flexibility.

Feature proposals can be tested with five questions:

1. Does this make a common participant interaction simpler?
2. Does it coordinate meaningful participant progression, or record unrelated
   operational detail?
3. Is it survey-driven operational work, or an external professional workflow?
4. Can it happen safely without human judgement?
5. Would an integration or explicit handoff preserve the boundary better than
   owning the activity?

## Adoption implication

This boundary would let a research team adopt FlowForm without moving every
study activity into it. Researchers could continue using a spreadsheet,
calendar, REDCap, a hospital system, or an informal process after FlowForm
surfaces the information they need.

The narrower promise may therefore be more useful than describing FlowForm as
a general participant workflow platform: it identifies what the product should
do exceptionally well and makes coexistence with specialist systems explicit.

## Questions still open

- Which proposed interactions and automations belong in the first complete
  product journey?
- What level of participant status is useful without becoming case management?
- Which gates can be evaluated directly and which only record human approval?
- Which automation actions need acknowledgement, escalation, or audit records?
- Should research-specific concepts such as “study” remain primary in the
  interface, or be expressed through templates over more neutral concepts?
- Which safety and consent boundaries require explicit product policy before
  automation is introduced?

## Related documents

- [[ideas-index|Engineering ideas]]
- [[product-index|Product knowledge]]
- [[builder-and-rules|Builder and rules]]
- [[respondent-access-and-continuity|Respondent access and continuity]]
- [[market-and-commercial-hypotheses|Market and commercial hypotheses]]
