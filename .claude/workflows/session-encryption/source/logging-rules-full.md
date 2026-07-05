# Logging Rules — Full Reference

## Do Not Log

- Plaintext answers or decrypted answer payloads.
- Plaintext DEKs, wrapped DEKs, KMS plaintext, full KMS key ARNs, or linkage secrets.
- Raw public-link tokens, `flowform_submission_session` values, `flowform_subject_recognition` values, or auth cookies.
- Full response DB locators, ciphertext, nonces, request bodies, response bodies, or cookie/header blobs.

## Safe Fields

- Prefer existing request metadata: `request_id`, method, path, status code, remote address, and duration.
- Error responses/logs may include `AppError.code`, safe messages, status codes, and non-secret row IDs or UUIDs such as session, envelope, answer, and revision IDs.
- When a token reference is necessary, use only an existing stored prefix such as `token_prefix`; do not derive or print new prefixes from raw tokens.

## Observability Integrations

Sentry is not configured in the current codebase. If Sentry, tracing, or richer request logging is added, install an explicit allowlist sanitizer before capture; do not rely on blocklists.
