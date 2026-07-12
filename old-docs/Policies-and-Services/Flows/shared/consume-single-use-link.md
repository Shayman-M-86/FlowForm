# Sub-flow: Consume single-use link

Shared by:

* Private assigned link
* Authenticated assigned link

General links are reusable and are never consumed.

---

## Rule

Backend marks the link as used by setting `used_at`.

This must happen atomically with submission session creation.

The link must only be consumed if the submission session is successfully created.

If session creation fails, the link must not be marked as used.

After the link is consumed, any further attempt to resolve or start a session with the same link token is rejected.

---

## Transaction boundary

For single-use links, the session-start transaction should include:

* final subject resolution effects, including canonical merge updates if required
* submission session creation
* `used_at` update on the link
* recognition token issue or rotation, if required

If any part fails, the transaction should roll back.
