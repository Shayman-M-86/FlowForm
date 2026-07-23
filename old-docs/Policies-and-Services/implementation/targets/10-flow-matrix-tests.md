# Target 10: Flow Matrix Tests

Goal: make tests describe the behavior matrix, not just old module behavior.

Relevant docs:

* `../flow-matrix.md`
* all access flow docs as needed by selected test group

Likely files:

* new or migrated public-submissions integration tests
* scenario-table tests for subject/token decisions
* route contract tests for cookies and response shapes

Expected coverage:

* one happy path per access method
* one rejection path per access method
* canonical-subject merge regression cases
* token keep/issue/rotate/mark-used decisions

Risk: medium.

Stop if tests need behavior changes not yet implemented by earlier targets.
