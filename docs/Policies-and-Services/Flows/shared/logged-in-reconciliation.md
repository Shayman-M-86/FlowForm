# Sub-flow: Logged-in reconciliation

Shared by:

* Public slug
* General link

This is the open-access branch of [subject-resolution.md](subject-resolution.md).

It applies only when the access method is public slug or general link.

For private and authenticated assigned links, do not use this sub-flow. Assigned-access subject resolution applies instead.

---

## Inputs

At this point the backend has:

* validated the access method
* determined whether the respondent is logged in
* attempted recognition token lookup through [check-recognition-token.md](check-recognition-token.md)
* loaded the logged-in user's project identity subject, if one exists

---

## Authority order

1. Logged-in identity subject
2. Recognition token subject
3. New anonymous `ProjectSubject`

The logged-in identity subject always wins over the token subject.

---

## Decision table

| Logged in | Token subject | Existing identity subject | Final subject | Side effect |
| --- | --- | --- | --- | --- |
| No | None | None | New anonymous subject | Issue recognition token |
| No | Valid | None | Token subject | Update token `last_used_at` |
| Yes | None | No | New subject for logged-in user | Create user identity; issue recognition token |
| Yes | Valid | No | Token subject | Attach user identity to token subject; update token `last_used_at` |
| Yes | None | Yes | Identity subject | Issue recognition token to identity subject |
| Yes | Valid, canonical same as identity | Yes | Identity subject | Update token `last_used_at`; keep token if it already points to the canonical identity subject, otherwise rotate to canonical subject |
| Yes | Valid, canonical different from identity | Yes | Identity subject | Set token subject `canonical_subject_id` to identity subject; rotate token to identity subject |

---

## Conflict rule

When the token subject and logged-in identity subject are different:

* keep the logged-in identity subject as canonical
* set `canonical_subject_id` on the token subject row to the identity subject ID
* use the identity subject for the submission session
* rotate the browser recognition token so future requests resolve to the identity subject

---

## Output

Return the subject-resolution result described in [subject-resolution.md](subject-resolution.md):

* `final_subject_id`
* `subject_source`
* merge action, if needed
* token action, if needed

---

See also: [core-policies.md — Public slug and general link](../../core-policies.md#public-slug-and-general-link).
