"""Concept-only scaffold for future tests.

Original suggested path: tests/unit/services/public_submissions/actions/test_answer_save_service.py

Concepts:
- validates question exists
- validates answer shape
- skips validation for cleared answer
- derives answer locator
- calls encryption
- writes answer slot
- writes encrypted response
- records answer saved event
- rejects non-in-progress session

Notes:
This can be unit-tested with mocked repositories, but the real confidence should
come from integration tests because answer save crosses DB, validation,
encryption, and response storage.

Implementation intentionally omitted.
"""
