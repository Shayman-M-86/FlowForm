# Logging Rules

Never log: plaintext answers, DEKs (plain or wrapped), linkage secrets, KMS key material, resume tokens, link tokens, recognition tokens, auth cookies, ciphertext, nonces, or full locators.
Safe to log: `AppError.code`, status codes, non-secret row IDs, request method/path/duration.

**Before writing any logging calls**, add a todo item:
"Read `.claude/workflows/session-encryption/source/logging-rules-full.md` for safe fields and observability guidance."
Do NOT skip this — the stub above is a summary, not the full specification.
