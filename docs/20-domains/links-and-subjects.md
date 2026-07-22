---
title: Links and subjects
aliases:
  - "Links and subjects"
document_type: domain
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [security]
related_code:
  - "../../backend/app/services/survey_links.py"
  - "../../backend/app/services/participants.py"
  - "../../backend/app/services/public_submissions/core/resolution/"
  - "../../backend/app/schema/orm/core/project_subject.py"
  - "../../backend/app/schema/orm/core/survey_access.py"
  - "../../backend/tests/integration/core/test_flow_matrix.py"
related_docs:
  - "Identity and authentication"
  - "Submissions"
  - "Security model"
---

# Links and subjects

Defines respondent entry credentials and the project-scoped pseudonymous subject
that provides continuity across survey attempts. Auth0 account identity remains
owned by [[identity-and-authentication|Identity and authentication]], while this
domain decides how a link, browser token, participant, and authenticated actor
resolve to a subject.

## Purpose

FlowForm needs to support anonymous, bearer-link, assigned, and authenticated
survey entry without making every respondent a project member. This domain
separates the access credential from the stable subject record and reconciles
stronger identity evidence with prior browser recognition.

## Responsibilities

- Create and administer general, private, and authenticated survey links,
  including activation, expiry, assignment, use, and email-delivery metadata.
- Maintain project subjects, revocable email/authenticated-user identities,
  reusable recognition-token hashes, and enrolled participants.
- Require private and authenticated links to carry one assigned participant;
  general links carry no participant assignment.
- Resolve open access by the priority `authenticated identity > recognition
  token > new anonymous subject`.
- Resolve assigned links to their participant's subject, merge weaker subject
  continuity into the stronger subject where needed, and issue or rotate the
  recognition token.
- Enforce link state, visibility compatibility, authentication, participant
  assignment, and actor matching before session creation.

## Non-responsibilities

- A project subject is not a Studio user, project membership, or authorization
  role.
- A participant is an enrolled subject plus one identity; it is not every
  respondent and it does not store an answer.
- A survey-link token is not the browser submission-session token and does not
  resume answer writes after a session has started.
- This domain selects subject/access context but does not create encrypted
  response envelopes or advance the submission lifecycle.

## Main entities and invariants

| Entity | Role | Important invariant |
| --- | --- | --- |
| Project subject | Stable UUID plus unique project-scoped subject code | An alias may point to a canonical subject in the same project and may not point to itself. |
| Subject identity | Revocable email or authenticated-user attachment | Authenticated identities carry both user ID and the user's current normalized email; at most one active user identity exists per project. |
| Recognition token | Returning-browser credential | Raw 32-byte-random token is held in a cookie; only its SHA-256 hash, expiry, use, and revocation state are persisted. |
| Participant | Subject enrolled under a specific identity | Composite keys prove the participant, subject, and identity all belong together in one project. |
| Survey link | Bearer token for one survey | Token is unique; assignment and link type are coherent; assigned links are single-use by domain rule. |

Survey-link tokens are stored in plaintext because resolution performs a direct
lookup. Recognition and submission-session tokens differ: their raw values are
never stored in core data.

## Important workflows

1. An administrator enrolls a participant by creating a subject, unverified
   email identity, and participant row, then creates an assigned link if needed.
2. Link resolution checks active/expiry/use state, loads the survey's current
   published version and response store, and applies link-type authentication
   and assignment policy.
3. For public-slug or general-link access, an authenticated subject wins over a
   valid recognition token; otherwise the token subject or a new anonymous
   subject is used.
4. For private/authenticated assigned access, the assigned subject always wins.
   A different token subject is made an alias of that subject and its token is
   rotated.
5. An authenticated link whose participant still has an email identity can be
   upgraded to an authenticated-user identity when the actor's normalized email
   matches; link resolution then requires that exact user.
6. Session start applies the subject merge/identity/token instructions and marks
   an assigned link used in the same core transaction as the new session.

## Implementation map

- `backend/app/services/survey_links.py` and
  `backend/app/repositories/public_link_repo.py` own administrative link state.
- `backend/app/services/participants.py` and `subjects.py` own participant and
  subject administration.
- `backend/app/services/public_submissions/core/resolution/access_resolver.py`
  validates respondent entry; `subject_resolver.py` calculates subject priority,
  merge, and token actions; `session_subject_service.py` applies the writes.
- `backend/app/schema/orm/core/project_subject.py`, `project_participant.py`, and
  `survey_access.py` map the domain; the core SQL schema contains its definitive
  composite and partial constraints.
- The integration flow matrix exercises open, assigned, authenticated, token,
  merge, and rejection combinations.

## Verified gaps and open questions

- Upgrading an assigned email identity to an authenticated-user identity checks
  normalized email equality but does not require the local/Auth0 email to be
  verified first.
- Single-use enforcement performs a state check before session creation and
  marks `used_at` later without an atomic conditional update or locked link row;
  concurrent starts are not covered by the sequential lifecycle tests.
- Studio link listing returns the persisted bearer token to callers with
  `survey:view`; the intended token-disclosure and rotation policy is not stated.
- Subject resolution follows at most one canonical alias hop, while the schema
  does not independently prohibit longer alias chains.
- Recognition tokens live for 365 days in the current repository and are scoped
  across surveys in a project. Product and privacy policy for lifetime,
  revocation, and user-facing reset is not documented.
- Participant deletion is intentionally blocked while any survey link assigns
  it; cleanup ordering and account-deletion behavior need an explicit workflow.

## Related documents

- [[identity-and-authentication|Identity and authentication]]
- [[submissions|Submissions]]
- [[security-model|Security model]]
