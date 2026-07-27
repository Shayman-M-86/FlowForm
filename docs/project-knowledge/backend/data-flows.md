---
title: Data flows
aliases: ["Data flows"]
document_type: architecture
status: draft
authority: canonical
verified_against_commit: null
tags: [backend, frontend, security]
related_code:
  - "../../../backend/app/api/v1/"
  - "../../../backend/app/services/surveys.py"
  - "../../../backend/app/services/public_submissions/"
  - "../../../backend/app/services/results.py"
  - "../../../backend/app/crypto/"
  - "../../../backend/app/schema/orm/"
related_docs:
  - "Backend knowledge"
  - "Surveys and versioning"
  - "Links and subjects"
  - "Submissions"
  - "Responses and encryption"
---

# Data flows

This draft maps the major runtime paths through the Studio/respondent clients,
the Flask backend, core metadata, and encrypted response storage. It is a
boundary map, not an endpoint or field catalogue.

| Flow | Initiator | Core metadata | Response storage |
| --- | --- | --- | --- |
| Survey authoring and publication | Studio user | survey, draft/version, compiled rules | publication prepares a destination/key boundary |
| Respondent entry | respondent browser | link, subject, session metadata | response envelope is created |
| Answer save and completion | respondent browser | slots and lifecycle events | encrypted answer payloads are upserted |
| Results access | Studio user | survey/session metadata | ciphertext is read through the authorized service boundary |
| Recovery | reconciliation work | incomplete sessions may be marked abandoned | envelope presence is checked |

```text
Studio authoring ------------------------------------+
   |                                                  |
   v                                                  |
Core: project -> survey -> draft -> published version |
   |                                                  |
   +--> respondent access -> submission session ------+
                              |
                    +---------+---------+
                    |                   |
                    v                   v
              Core metadata      encrypted response data
                    \                   /
                     +---- results ----+
```

The legacy design records no SQL join between the two stores. Cross-store
references use derived opaque locators, so a workflow must explicitly order its
commits and handle partial failure. [[submissions|Submissions]] owns the
respondent lifecycle; [[responses-and-encryption|Responses and encryption]]
owns the encryption/data boundary.

## Related documents

- [[backend-index|Backend knowledge]]
- [[surveys-and-versioning|Surveys and versioning]]
- [[links-and-subjects|Links and subjects]]
- [[submissions|Submissions]]
