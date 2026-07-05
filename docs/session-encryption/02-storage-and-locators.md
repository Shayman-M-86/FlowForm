# Storage Split and Locators

## Purpose

This document explains how the core database and response database are connected without giving the response database identifying metadata.

## Core database

The core database stores application metadata:

- project, survey, and version records;
- public and restricted survey links;
- respondent identity and subject records;
- submission sessions;
- session lifecycle state;
- analytics events.

The core database stores respondent identity metadata and session origin metadata. It must not store plaintext answers.

## Response database

The response database stores encrypted answer material:

- response envelopes;
- logical answer rows;
- immutable answer revisions;
- ciphertext;
- nonces;
- locally wrapped per-session DEKs;
- crypto version.

The response database must not store:

- user IDs;
- project IDs;
- survey IDs;
- link IDs;
- project subject IDs;
- participant IDs;
- identity IDs;
- emails;
- IP addresses;
- recognition tokens;
- browser resume tokens;
- core session UUIDs;
- plaintext question IDs;
- plaintext answers;
- KMS key ARNs;
- KMS context versions.

## No direct database join

There must be no SQL foreign key from the response database back to the core database.

The backend connects the two stores by deriving opaque values from core identifiers using versioned linkage-secret material.

## Session locator

A session locator identifies one response envelope from one core submission session.

Conceptually:

- input: core submission session ID;
- secret: active linkage secret for that session's linkage version;
- output: opaque session locator stored in the response database.

The response database sees only the locator. It does not see the core session UUID.

## Answer locator

An answer locator identifies one logical question answer inside one response envelope.

Conceptually:

- input: core submission session ID plus question node ID;
- secret: linkage secret for that session's linkage version;
- output: opaque answer locator stored in the response database.

The answer locator lets the backend update the same logical answer without exposing the plaintext question ID.

## Why the encrypted payload still includes the question ID

The response row uses an answer locator so the database can upsert and locate answers privately.

The encrypted payload must also contain the real question node ID. After decryption, the backend recomputes the answer locator and verifies that the decrypted question ID matches the row. This is a defensive check against row substitution and accidental data corruption.

## Versioning rule

Locator derivation must be versioned. A stored session must carry enough version metadata for the backend to regenerate the correct locator later.

New sessions use the active linkage version. Old sessions remain readable through their stored linkage version.
