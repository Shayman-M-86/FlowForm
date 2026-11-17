---
title: Business tracing
aliases:
  - "Business tracing"
  - "Tracing API"
document_type: implementation
status: draft
authority: canonical
verified_against_commit: null
tags: [backend]
related_code:
  - "../../../backend/app/tracing/"
  - "../../../backend/app/tracing/api.py"
  - "../../../backend/app/tracing/policy.py"
  - "../../../backend/app/tracing/vocabulary.py"
  - "../../../backend/app/logging/logging_config.py"
  - "../../../backend/app/logging/sensitive_data.py"
  - "../../../backend/app/middleware/auth/auth0.py"
  - "../../../backend/app/services/access/access_service.py"
  - "../../../backend/app/services/account.py"
  - "../../../backend/app/services/admin_results/"
  - "../../../backend/app/services/public_submissions/"
  - "../../../backend/app/services/surveys.py"
  - "../../../backend/app/email_service/sender.py"
  - "../../../backend/tests/unit/tracing/"
related_docs:
  - "Backend implementation guides"
  - "Backend configuration patterns"
  - "Observability"
  - "Distributed tracing"
  - "Responses and encryption"
---

# Business tracing

Explains the FlowForm-owned tracing surface — `action`, `fields`, `event` — and
the rules for putting data into a trace. This is a thin business layer over the
existing OpenTelemetry bootstrap; it observes the current service layer and does
not reshape it. The code in `backend/app/tracing/` remains authoritative when a
guide and the implementation differ.
The tracing implementation is currently in the working tree, so this draft has
no committed verification baseline yet.

## What already exists underneath

FlowForm already has working distributed tracing before any of this API is used:
automatic Flask request spans, propagation from the edge, export to the
configured OTLP endpoint, and trace/span IDs injected into every log record.
This layer adds the ability to see *which business action* ran, *how far it
got*, and *what kind of thing it was* — without smearing OpenTelemetry calls
through the services or exporting sensitive survey data.

Import the surface as a namespace:

```python
from app import tracing
```

## The three primitives

### `action(name)` — open a span

`action` marks a business operation with its own span. It is **both a decorator
and a `with` block** — the same object works either way, because
OpenTelemetry's `start_as_current_span` returns something usable as both.

```python
@tracing.action("submission.answer.save")
def save_answer(self, ...) -> AnswerSaveResult:
    ...
```

```python
with tracing.action("access.project_permission.check"):
    ...  # the permission decision
return view(*args, **kwargs)   # runs AFTER the span closes
```

Choose the form by scope:

- **Decorator** when the whole method *is* the operation (`save_answer`).
- **`with` block** when the span should cover only part of a function — a
  guard, a lookup — and the rest must run outside it. The permission decorators
  use this so the wrapped view is never inside the auth span.

You never set span status or record exceptions by hand. If an exception
propagates out of the span, OpenTelemetry records it as an `exception` event and
marks the span **errored** (red in Tempo) automatically. When tracing is
disabled or no provider is installed, `action` yields a non-recording span, so
it is a safe no-op — nothing dials out.

### `fields(**values)` — attributes on the span

`fields` attaches key/value attributes describing the span **as a whole**. One
value per key; setting it again overwrites; no timestamp.

```python
tracing.fields(question_type="single_choice", outcome="accepted")
```

Use a field to answer *"what was this span?"* — a property you will filter or
aggregate spans by (`outcome`, `question_type`). Fields are the searchable
dimensions of a span.

### `event(name, **values)` — a moment on the span's timeline

`event` records a timestamped point *inside* the span. Many per span, each with
its own time and optional attributes.

```python
tracing.event("flowform.submission.core_committed")
tracing.event("flowform.submission.response_committed")
```

Use an event to answer *"what happened, and when, during this span?"* — where
the **time, order, or presence** of the moment is itself the signal. The answer
save flow is the motivating case: it commits two databases in sequence with no
enclosing transaction, so `core_committed` and `response_committed` are separate
events. A trace showing the first without the second is exactly the torn write
worth surfacing; a single "persisted" checkpoint would hide it.

## Field or event?

They are not interchangeable, and an event is not "a field with a timestamp".

| Use a **field** | Use an **event** |
| --- | --- |
| Describes the span as a whole | Marks a moment inside the span |
| One value; "when did it happen?" is nonsense | Timing / order / presence is the point |
| First-class, cheap to filter and aggregate | Buried one level down; weaker to query |
| `outcome`, `question_type`, `submission_mode` | `core_committed`, a state transition, a checkpoint |

Reach for a **field by default** — fields are what make a span searchable. Add
an **event** only when you can finish the sentence *"…and the timing, order, or
presence of this moment matters."* A terminal outcome does not need an event:
the span's own end timestamp already marks when it concluded, and the `outcome`
field crossed with span **duration** already tells you which path ran and how
long it took.

## What may go into a trace

Trace attributes leave the process and are retained in Tempo, so the bar is
strict. A value belongs in a trace only if it passes **both** tests:

1. **Bounded** — few possible values, from a known set. `question_type` (a
   category) is fine; a specific `question_node_id` (unbounded) is not.
2. **Non-identifying** — describes *what kind*, never *which one* or *whose*.
   `outcome="denied"` is fine; `user_id`, a subject, an email, or an answer is
   not — regardless of how useful it would be to filter on.

This is not "runtime data never goes in a trace." Runtime values go in freely
(`question_type`, `outcome`, `submission_mode` are all computed per request) as
long as each is bounded and non-identifying.

The policy is enforced, not merely documented. `filter_fields` in
[`policy.py`](../../../backend/app/tracing/policy.py) accepts only an
**allowlist** of field names and drops everything else, so even
`tracing.fields(user_id=...)` produces no trace attribute. The drop is logged
at WARNING (with throttling). The current allowlist
(`vocabulary.py`):

`outcome`, `checkpoint`, `question_type`, `submission_mode`,
`validation_error_count`, `answer_count`, `version_number`, `completion_state`,
`authentication_method`.

Extend it only with a documented operational need, and only with a bounded,
non-identifying name. Every exported value is additionally normalized and
capped: at most 24 fields per span, strings truncated to 256 chars, sequences to
32 elements, integers within the lossless float range. Non-finite floats and
unsupported types are dropped. **Violations are dropped and logged at WARNING,
never raised** — telemetry must never break a live request.

## Trace versus log

Traces and logs are complementary sinks, not redundant ones. Put a value where
its consumer lives:

- **Trace** (field/event): bounded, non-identifying, and something you will
  **aggregate or filter across many requests** — denial rates, p95 latency by
  `question_type`, the shape of an operation.
- **Log**: high-cardinality or identifying, and something you **read one
  request at a time** — `user_id`, a specific `survey_id`, a narrative message,
  a stack trace.

The two are already tied together. `LoggingInstrumentor`
([`extension.py`](../../../backend/app/tracing/extension.py)) stamps
`otelTraceID` / `otelSpanID` onto every log record emitted while a span is
current, and the JSON formatter
([`logging_config.py`](../../../backend/app/logging/logging_config.py)) emits
them as `trace_id` / `span_id`. So a log line written inside a span carries the
same `trace_id` as the trace in Tempo. You aggregate in traces to learn *that*
something happened, then pivot to logs by `trace_id` to see *who* and *which*.
The permission decorators use exactly this split: `outcome="denied"` on the span
(queryable), `user_id` / ids / `permission` in a WARNING log (per-incident).

## Naming rules

Names are structural labels only and must never carry a runtime value.

- **Action**: `<domain>.<entity>.<verb>` — 3–64 chars, contains `.`, lowercase
  letters / `.` / `_` only, no leading or trailing dot. Example:
  `submission.answer.save`.
- **Event**: an action name that additionally starts with `flowform.`. Example:
  `flowform.submission.core_committed`.

An invalid **action** name falls back to a generic span name (the span still
records); an invalid **event** name is dropped. Both log the rejection.

## Current action inventory

The current inventory intentionally contains a small set of workflow owners,
not every route, CRUD method, repository query, crypto helper, or provider SDK
call. Automatic OpenTelemetry instrumentation remains responsible for the
database, HTTP, and AWS child spans beneath these actions.

| Action | Workflow owner | Primary signal |
| --- | --- | --- |
| `auth.access_token.verify` | authentication decorators | access-token verification and any Auth0/JWKS HTTP work |
| `access.project_permission.check` | project RBAC decorator | project permission decision |
| `access.survey_permission.check` | survey RBAC decorator | survey permission decision |
| `submission.session.start` | `SessionStarter.start` | respondent entry and the cross-store session creation sequence |
| `submission.subject.resolve` | `SessionSubjectService.resolve_for_session_start` | subject/recognition-token resolution inside session start |
| `submission.answer.save` | `AnswerSaveService.save_answer` | answer encryption and the core/response write sequence |
| `submission.session.complete` | `complete_session` | completion transition and cache eviction |
| `survey.version.publish` | `SurveyService.publish_version` | version compilation, publication, and encryption-store preparation |
| `results.export.generate` | `AdminResultsService.export_results` | result assembly, optional decryption, and file formatting |
| `results.session.delete` | `AdminResultsService.delete_session` | response-first, then core-session deletion |
| `account.email_verification.check` | `UserAccountService.check_email_verified` | cached or live Auth0 verification check |
| `email.message.send` | `SesEmailSender.send` | SES delivery or the intentional disabled-send path |

`submission.session.start` emits response and core commit events, while
`results.session.delete` emits response and core deletion events. These pairs
make the order and partial completion of the two-store workflows visible
without exporting any identifying data.

## Adding a span to a new operation

1. Decorate the **workflow owner**, not a thin delegator. Where a service has an
   `api/` façade delegating to a `core/` action, the span goes on the `core`
   method that owns the work — the auto Flask request span already covers the
   HTTP edge, and double-spanning a façade and its service adds noise.
2. Add `tracing.fields(...)` at the natural points, using only allowlisted,
   bounded, non-identifying values. Let expected rejections that return normally
   record an `outcome`; leave raised exceptions to OpenTelemetry.
3. Add a `tracing.event(...)` only for an interior moment whose timing, order,
   or presence matters.
4. Keep identifying detail out of the span. If you need it for debugging, log it
   — the shared `trace_id` links the two.

## Tests and remaining proof

`backend/tests/unit/tracing/test_api.py` covers the public
`action`/`fields`/`event` surface, while `test_policy.py` covers allowlisting,
normalization, and bounds. `test_extension.py` and `test_provider.py` cover the
OpenTelemetry bootstrap and provider lifecycle. Focused application tests cover
the affected session, subject, survey, and account behaviour without requiring
an external telemetry service.

Live Tempo delivery, attribute appearance, trace/log correlation, and the
absence of sensitive values still need deliberate environment-level
verification; a passing unit suite cannot prove those operational properties.

## Related documents

- [[40-implementation/backend/README|Backend implementation guides]]
- [[backend-configuration-patterns|Backend configuration patterns]]
- [[observability|Observability]]
- [[tracing|Distributed tracing]]
- [[responses-and-encryption|Responses and encryption]]
