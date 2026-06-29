"""Concept-only scaffold for future tests.

Original suggested path: tests/unit/services/public_submissions/session/test_session_loader.py

Concepts:
- missing resume token rejected
- unknown token rejected
- expired session rejected
- abandoned session rejected
- completed session rejected for answer save
- completed session allowed for idempotent completion
- cached context reused
- stale cached context evicted

Notes:
This should stay focused on loading/guarding session state. The current loader
does token hashing, session lookup, expiry/status checks, locator/envelope
loading, and cache use, so this is a good place to keep those behaviours
isolated.

Implementation intentionally omitted.
"""
