# Target 03: RecognitionTokenLookupResult

Goal: make token lookup return candidate metadata only. Lookup must not decide
final subject or token action.

Relevant docs:

* `../../core-policies.md`
* `../../Flows/shared/check-recognition-token.md`
* `../../Flows/shared/subject-resolution.md`

Likely files:

* `backend/app/services/public_submissions/core/subject_token.py`
* `backend/app/repositories/core/project_subject_tokens.py`
* `backend/app/repositories/core/project_subjects.py`
* `backend/app/services/results.py`

Expected direction:

* return token metadata, not only `ProjectSubject | None`
* include token id, original token subject, canonical token subject
* do not update `last_used_at` during lookup unless subject resolution asks for it
* preserve raw token secrecy

Risk: medium. Raise to high if token validity or rotation semantics change.

Stop if canonical subject helper behavior must be designed first.
