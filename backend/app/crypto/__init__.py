"""Session encryption for FlowForm survey responses.

Key hierarchy (each tier wraps the one below; see _internal/KEY_HIERARCHY.md):

    KMS
     └─ survey key      (one per survey)      survey_key.py
         └─ session key (one per session)     session_key.py
             └─ answer  (one per revision)    answers.py

Public modules
--------------

survey_key  (tier 1) — keyed in cache by (project_id, survey_id)
    wrapped_survey_key_exists        — whether a survey key exists (cache then DB)
    create_wrapped_survey_key        — mint, wrap, and persist a new key (on publish)
    load_plaintext_survey_key        — plaintext key by ids; no DB on cache hit
    start_plaintext_survey_key_load  — start a background unwrap, returns a resolver
    clear_plaintext_survey_key       — evict a plaintext key from cache
    Side effects: cache read/write, DB read + KMS API on cache miss

session_key  (tier 2)
    create_session_key            — generate and wrap a new per-session key
    load_plaintext_session_key    — unwrap a stored session key (cached)
    clear_plaintext_session_key   — evict a plaintext key from cache
    Side effects: cache read/write

answers  (tier 3)
    encrypt_answer_current   — encrypt an answer before storage
    decrypt_answer_current   — decrypt a stored answer for admin viewing
    Side effects: none (pure crypto)

locators  (separate chain — pseudonymous IDs, not key wrapping)
    load_current_linkage_key         — load the active linkage key
    derive_session_locator           — derive with caller-provided linkage key
    resolve_new_session_locator      — load current key + derive session locator
    resolve_existing_session_locator — load historical key + derive session locator
    derive_answer_locator            — derive with caller-provided linkage key
    resolve_answer_locator(s)        — load historical key + derive answer locators
    Side effects: cache read/write, Secrets Manager API on cache miss,
                  DB read/write for linkage key version mapping

models
    AnswerContext       — AAD fields shared by encrypt/decrypt
    SessionDEKContext   — session identity used to build the wrap AAD
    NewSessionDEK       — plaintext + wrapped session key pair
    NewSessionLocator   — locator + linkage key version
    LinkageKey          — versioned linkage secret

Internal modules live in _internal/ and should not be imported by services.
"""
