# Pass 03: AWS Wiring and Crypto Smoke Test

Read `.claude/workflows/session-encryption/working/targets/03-aws-wiring-and-crypto-smoke-test/spec.md` in full before writing any code.

Dependency checks:
- Confirm `backend/app/crypto/aes_gcm.py` exists (pass 01). If not, stop.
- Confirm `backend/app/repositories/response/` exists (pass 02). If not, stop.
- Confirm `ENCRYPTION_KMS_KEY_ARN` and `ENCRYPTION_LINKAGE_SECRET_ARN` are set. If not, stop and tell the operator what AWS resources need provisioning (see spec "Human action required" section).

New files go in `backend/app/crypto/`. Use boto3. Load all ARNs and region from env vars — never hardcode. All secrets fetched at call time or cached in `DekCache` — never stored as module-level globals.

{{context: context/code-conventions.md}}

{{context: context/logging-rules.md}}

{{context: context/validation-ladder.md}}

{{context: context/testing-patterns.md}}

After implementing, run: `bash backend/scripts/run-tests.sh --ai -k "crypto_smoke"`

{{context: context/pass-report-template.md}}
