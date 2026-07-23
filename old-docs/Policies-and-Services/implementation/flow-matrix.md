# Behavioral Flow Matrix

Use this table as agent-readable target derived from policy docs. Do not treat it
as replacement for docs.

| Entry | Logged in? | Token state | Assigned? | Final subject authority | Token action | Link consumed? | Transaction requirement |
| --- | ---: | --- | ---: | --- | --- | --- | --- |
| public slug | no | none | no | new anonymous subject | issue | no | session + token effects commit together |
| public slug | no | valid canonical | no | token subject | mark used/keep | no | session + token effects commit together |
| public slug | yes | none | no | logged-in identity or new user subject | issue | no | identity/session/token effects commit together |
| public slug | yes | valid, same canonical as identity | no | logged-in identity subject | mark used/keep | no | identity/session/token effects commit together |
| public slug | yes | valid, different canonical | no | logged-in identity subject | merge weaker token subject, rotate | no | merge/session/token effects commit together |
| general link | no | none | no | new anonymous subject | issue | no | session + token effects commit together |
| general link | no | valid canonical | no | token subject | mark used/keep | no | session + token effects commit together |
| general link | yes | none | no | logged-in identity or new user subject | issue | no | identity/session/token effects commit together |
| general link | yes | valid, same canonical as identity | no | logged-in identity subject | mark used/keep | no | identity/session/token effects commit together |
| general link | yes | valid, different canonical | no | logged-in identity subject | merge weaker token subject, rotate | no | merge/session/token effects commit together |
| private link | any | none | yes | assigned subject | issue if needed | yes on session start | session/token/link consumption commit together |
| private link | any | valid, same canonical as assigned | yes | assigned subject | keep | yes on session start | session/token/link consumption commit together |
| private link | any | valid, different canonical | yes | assigned subject | merge weaker token subject, rotate | yes on session start | merge/session/token/link consumption commit together |
| authenticated link | no | any | yes | none | none | no | access rejected before subject resolution |
| authenticated link | yes, matching assigned identity | none | yes | assigned subject | issue if needed | yes on session start | session/token/link consumption commit together |
| authenticated link | yes, matching assigned identity | valid, same canonical as assigned | yes | assigned subject | keep | yes on session start | session/token/link consumption commit together |
| authenticated link | yes, matching assigned identity | valid, different canonical | yes | assigned subject | merge weaker token subject, rotate | yes on session start | merge/session/token/link consumption commit together |
| authenticated link | yes, non-matching identity | any | yes | none | none | no | access rejected before subject resolution |
| authenticated account-linking | yes, email matches assigned identity | valid, different canonical | yes | assigned subject | merge weaker token subject, rotate | no | identity/token effects commit consistently |

Add rows in target-local plan only when docs require a more specific branch.
