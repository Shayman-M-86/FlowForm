# Pass 03: AWS Wiring and Crypto Smoke Test

## Goal

This is a validation pass. The agent wires the KMS and Secrets Manager
integrations and verifies that the crypto helpers from pass 01 work correctly
against real AWS infrastructure. The human operator must provision the AWS
resources before this pass can complete.

## Human action required before agent proceeds

The operator must:

1. Create a KMS symmetric key in the target AWS region and note the key ARN.
2. Create a Secrets Manager secret containing the linkage secret (random 32-byte
   value, base64-encoded) and note the secret ARN and version.
3. Set the following environment variables in the backend `.env` / Docker config:
   - `ENCRYPTION_KMS_KEY_ARN`
   - `ENCRYPTION_LINKAGE_SECRET_ARN`
   - `AWS_REGION`
   - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (or use instance role)

## Files to create

- `backend/app/crypto/kms.py` — `wrap_dek(plaintext_dek, key_arn, context) -> bytes`, `unwrap_dek(wrapped_dek, key_arn, context) -> bytes`
- `backend/app/crypto/secrets.py` — `get_linkage_secret(secret_arn, version_id) -> bytes`
- `backend/app/crypto/dek_cache.py` — worker-local DEK cache with TTL and eviction

## In scope

- `wrap_dek` / `unwrap_dek` using boto3 KMS `encrypt` / `decrypt`
- `get_linkage_secret` using boto3 Secrets Manager `get_secret_value`; supports version_id for rotation
- `DekCache`: cache key = session locator (bytes), TTL = no longer than session expiry, evict on session complete/expire/abandon/worker restart
- Config loading for KMS key ARN and secret ARN from environment variables
- A smoke-test script or integration test that: fetches the linkage secret, derives a session locator, generates a DEK, wraps it with KMS, unwraps it, encrypts a dummy payload, decrypts it, and asserts round-trip equality

## Decisions locked by source docs

- Cache key is session locator — not envelope ID (doc 05)
- DEK cache TTL must not exceed session expiry (doc 05)
- Evict on session complete, expired, abandoned, worker restart (doc 05)
- Linkage secret must not live in Postgres — only fetched from Secrets Manager (doc 05)
- Never log plaintext DEKs, wrapped DEKs, or raw linkage secrets (doc 06)

## Out of scope

- Session start or answer save — passes 04 and 05
- Response database writes

## Done when

- [ ] `wrap_dek` / `unwrap_dek` call real KMS and round-trip cleanly
- [ ] `get_linkage_secret` fetches from real Secrets Manager
- [ ] DEK cache implemented with correct eviction rules
- [ ] Smoke test passes against real AWS: `bash backend/scripts/run-tests.sh --ai -k "crypto_smoke"`
- [ ] No key material appears in logs during the smoke test run

## Dependencies

Passes 01 and 02 must be complete. Human must provision AWS resources first.
