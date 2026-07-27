---
title: Respondent access and continuity
aliases: ["Respondent access and continuity"]
document_type: domain
status: draft
authority: canonical
verified_against_commit: null
tags: [backend, security]
related_code:
  - "../../../backend/app/domain/public_link_rules.py"
  - "../../../backend/app/domain/submission_access_rules.py"
  - "../../../backend/app/domain/survey_rules.py"
  - "../../../backend/app/services/survey_links.py"
  - "../../../backend/app/services/public_submissions/core/resolution/"
  - "../../../backend/app/schema/orm/core/project_subject.py"
  - "../../../backend/app/schema/orm/core/survey_access.py"
  - "../../../backend/tests/integration/core/test_flow_matrix.py"
related_docs:
  - "Product knowledge"
  - "Links and subjects"
  - "Submissions"
  - "Identity and authentication"
---

# Respondent access and continuity

FlowForm separates three product questions that are easy to confuse:

1. May this request reach the published survey?
2. Which project-scoped subject represents the respondent?
3. May a submission session now be created?

An entry credential answers the first question. Identity, assignment, and
recognition evidence answer the second. A session starts only after both have
been resolved. A survey link or browser cookie is therefore not itself the
respondent and does not become the durable submission identity.

```text
survey reachability          respondent continuity
-------------------          ---------------------
visibility                   assigned participant
entry method                 authenticated identity
link state                   recognition token
publication state            anonymous subject
          \                       /
           +---- validated ------+
                     |
                     v
             submission session
```

## Survey reachability

A survey must have a published version and a configured response store before a
respondent session can start. Visibility then limits the entry methods that may
reach it:

| Visibility | Product meaning | Accepted respondent entry |
| --- | --- | --- |
| `public` | Publicly browsable through its slug | Public slug, general link, or assigned link |
| `link_only` | Not publicly listed or slug-accessible | General link or assigned link |
| `private` | Restricted to a pre-assigned participant | Private or authenticated assigned link |

Public surveys require a public slug. A non-public survey cannot carry one.
Changing visibility is also respected when an existing link is resolved; an
old general link does not bypass a later change to `private`.

Every link must be active, unexpired, compatible with the survey visibility,
and unused when it is single-use. These checks apply both when resolving a link
for respondent display and when starting the submission.

## Link types and assignment

FlowForm has three survey-link types:

| Link type | Assignment | Reuse | Additional identity rule |
| --- | --- | --- | --- |
| `general` | Must not have an assigned participant | Reusable | None |
| `private` | Must have an assigned participant | Single-use | Possession of the link is sufficient |
| `authenticated` | Must have an assigned participant | Single-use | The logged-in user must match the participant identity |

An assigned participant connects a project subject to an identity. For an
authenticated link, an unlinked identity triggers the account-linking flow;
after linking, the authenticated user must match that identity. Authentication
verifies the assignment but does not replace the assigned subject with a
different user-associated subject.

Single-use consumption is part of successful session creation. A failed start
must not leave the assigned link consumed while no usable session exists.

## Subject authority

A project subject is the stable, project-scoped representation of a respondent.
The same person may initially be observed through anonymous browser continuity,
an authenticated account, or an assigned participant. Resolution chooses one
canonical subject for the session.

Open access through a public slug or general link uses this authority order:

1. the logged-in user's project identity;
2. a valid recognition-token subject;
3. a newly created anonymous subject.

Assigned access through a private or authenticated link uses the assigned
participant's subject. A recognition token can help reconcile browser
continuity, but it cannot override the assignment.

```text
open access                              assigned access
-----------                              ---------------
logged-in project identity               assigned participant subject
            |                                         |
            v                                         v
valid recognition subject                 token used only for reconciliation
            |
            v
new anonymous subject
```

When two observations refer to different subjects and stronger evidence wins,
the weaker subject becomes an alias of the canonical subject. Future resolution
uses the canonical record before comparing candidates. This preserves prior
references without treating two subject rows as two continuing respondents.

## Recognition tokens

A recognition token reconnects one browser to a subject within one project. It
supports continuity across surveys in that project, but it does not grant
survey access. The respondent must still present a valid slug or survey link.

Only a token hash is persisted. Missing, expired, revoked, malformed,
hash-mismatched, or wrong-project tokens provide no subject evidence. When
stronger identity or assignment evidence selects another canonical subject,
the browser token can be rotated to follow that subject.

Recognition tokens, survey-link tokens, browser resume tokens, and login
credentials are distinct:

| Credential | Purpose |
| --- | --- |
| Survey-link token | Reach one survey through a configured link |
| Recognition token | Recognize a returning browser within one project |
| Browser resume token | Resume one in-progress submission session |
| Login credential | Establish an authenticated user |

## Boundary with submission persistence

This product policy ends when access and subject context have been resolved.
Submission services then pin the attempt to a published survey version, create
core session metadata and encrypted response state, and return browser
credentials only after the required state exists.

The detailed service pipeline belongs to [[links-and-subjects|Links and
subjects]]. Session and answer persistence belong to [[submissions|Submissions]]
and [[responses-and-encryption|Responses and encryption]].

## Related documents

- [[product-index|Product knowledge]]
- [[links-and-subjects|Links and subjects]]
- [[submissions|Submissions]]
- [[identity-and-authentication|Identity and authentication]]
