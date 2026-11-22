# Documentation conventions

**Status: Current — documentation policy.**

Pages declare what a component owns, its dependencies and its interactions. They do not repeat generic coding rules. Architecture declarations explain structure; configuration references describe settings and their sources; runbooks specify procedures, expected outcomes and rollback steps.

Every implementation-sensitive page declares one of **Current**, **Target**, **Proposal**, or **Historical**. Changes to implementation require updates to the related page. Proposed changes belong in [Decisions](../decisions/README.md), not in the current-state architecture.

Prefer references to source files over copying configuration, secrets or generated API definitions. Link across repositories using stable URLs. Do not place credentials, tokens, private keys, participant records or production-only secrets in documentation.

A page has one authoritative home. Cross-link related pages rather than copying their contents.
