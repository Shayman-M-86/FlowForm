# Logical Flow

Quick-reference subject-resolution matrices. The durable policy lives in [core-policies.md](core-policies.md), with detailed sub-flows in [subject-resolution.md](Flows/shared/subject-resolution.md), [logged-in-reconciliation.md](Flows/shared/logged-in-reconciliation.md), and [issue-or-rotate-recognition-token.md](Flows/shared/issue-or-rotate-recognition-token.md).

---

## Open-access subject resolution

Used by:

* public slug
* general link

Authority order:

1. Logged-in identity subject
2. Recognition token subject
3. New anonymous `ProjectSubject`

| Logged in | Token subject | Existing identity subject | Final subject | Side effect |
| --- | --- | --- | --- | --- |
| No | None | None | New anonymous subject | Issue recognition token |
| No | Valid | None | Token subject | Update token `last_used_at` |
| Yes | None | No | New subject for logged-in user | Create user identity; issue recognition token |
| Yes | Valid | No | Token subject | Attach user identity to token subject; update token `last_used_at` |
| Yes | None | Yes | Identity subject | Issue recognition token to identity subject |
| Yes | Valid, canonical same as identity | Yes | Identity subject | Update token `last_used_at`; keep token if it already points to the canonical identity subject, otherwise rotate to canonical subject |
| Yes | Valid, canonical different from identity | Yes | Identity subject | Set token subject `canonical_subject_id` to identity subject; rotate token to identity subject |

The logged-in identity subject always wins over the recognition token subject for public slug and general link access.

---

## Assigned-access subject resolution

Used by:

* private assigned link
* authenticated assigned link
* authenticated assigned link account-linking

Authority order:

1. Assigned subject
2. Recognition token only for continuity cleanup

| Assigned subject | Token subject | Final subject | Side effect |
| --- | --- | --- | --- |
| Valid | None | Assigned subject | Issue recognition token to assigned subject if needed |
| Valid | Canonical same as assigned subject | Assigned subject | Keep token if it already points to the canonical assigned subject, otherwise rotate to canonical subject |
| Valid | Canonical different from assigned subject | Assigned subject | Set token subject `canonical_subject_id` to assigned subject; rotate token to assigned subject |

For authenticated assigned links, the logged-in user verifies access only. The logged-in identity must not override the assigned subject.
