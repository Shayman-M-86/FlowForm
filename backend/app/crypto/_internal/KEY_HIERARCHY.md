# Crypto key hierarchy

FlowForm protects answers with a 3-tier key chain. Each tier's key is
wrapped (encrypted) by the tier above it. Unwrapping flows top-down;
every tier caches its plaintext key after the first unwrap.

```
KMS (AWS, never leaves AWS)
  └─ wraps ─▶ Survey Branch Key   (one per survey)
                └─ wraps ─▶ Session DEK        (one per submission session)
                              └─ wraps ─▶ Answer payload  (current answer)
```

## What each tier's wrap/unwrap primitive is, and where it lives

All three live in `_internal/wrapping.py`, ordered top to bottom by tier.

| Tier | Key being protected | Protected by | Primitive (wrap / unwrap) |
|------|--------------------|--------------|---------------------------|
| 1 | Survey Branch Key | KMS (AWS API) | `wrap_dek_with_kms` / `unwrap_dek_with_kms` |
| 2 | Session DEK | Survey Branch Key (local AES) | `wrap_session_dek` / `unwrap_session_dek` |
| 3 | Answer payload | Session DEK (local AES) | `encrypt_answer` / `decrypt_answer` |

Tiers 2 and 3 are the **same** AES-256-GCM operation with different
parameter names and nonce handling. Tier 1 is the only one that calls
AWS.

## Public (root) modules that drive each tier

| Tier | Public module | Key entry points |
|------|---------------|------------------|
| 1 | `survey_key.py` | `create_wrapped_survey_key`, `load_plaintext_survey_key`, `start_plaintext_survey_key_load` |
| 2 | `session_key.py` | `create_session_key`, `load_plaintext_session_key` |
| 3 | `answers.py` | `encrypt_answer_current`, `decrypt_answer_current` |

## Supporting internals (not part of the key chain)

| File | Role |
|------|------|
| `wrapping.py` | the wrap/unwrap primitives for all three tiers |
| `aad.py` | builds the AAD that binds each ciphertext to its DB context |
| `kms_context.py` | builds the KMS encryption context binding a survey key to its survey |
| `nonces.py` | random nonce generation |
| `payload.py` | versioned plaintext answer encode/decode (tier 3) |
| `models.py` | low-level pydantic value types + byte-length constants |
| `client_extension.py` | holds the boto3 KMS + Secrets Manager clients |
| `errors.py` | crypto error types |

### Locator chain (separate from the DEK wrapping hierarchy)

| File | Role |
| ---- | ---- |
| `linkage_keys.py` | versioned linkage key access (cache + DB + AWS) |
| `linkage_secrets.py` | fetches linkage secrets from Secrets Manager |
| `locators.py` | HMAC locator derivation |

## Reading order to follow an unwrap

`survey_key.load_plaintext_survey_key`
→ `wrapping.unwrap_dek_with_kms`        (tier 1, KMS)
→ `session_key.load_plaintext_session_key`
→ `wrapping.unwrap_session_dek`         (tier 2, AES)
→ `answers.decrypt_answer_current`
→ `wrapping.decrypt_answer`             (tier 3, AES)
