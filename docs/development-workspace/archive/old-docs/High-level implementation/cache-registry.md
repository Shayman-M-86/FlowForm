# The Cache Registry

## Why a Registry, Not Just Some Dicts

FlowForm caches several unrelated things in-process — crypto key material,
session write context, an Auth0 email-verification flag — each with its own
key type, TTL, and capacity. Scattering ad-hoc module-level caches across the
codebase would mean no consistent way to enable/disable caching globally, no
single place to see what's cached where, and duplicated locking logic every
time someone reaches for another `TTLCache`. The registry exists to make
"add a new cache" a declarative, discoverable act rather than a bespoke one.

---

## Namespaces, Not a Flat Cache

`AppCache` (`cache/_registry.py`) holds a `CacheNamespace` per module —
currently `account`, `crypto`, `sessions`. Each namespace is a bag of typed
`CacheSpec` entries. Access is `cache.crypto.session_deks`, not a flat
`cache.get("session_deks")` — the namespace exists so cache items with
overlapping names or concerns in different domains don't collide, and so
enabling/disabling can be scoped later even though today it isn't (see Loose
Threads).

---

## Auto-Discovery, Not Manual Wiring

At startup, `create_app_cache()` calls `discover_cache_specs("app.cache")`,
which scans every module in `app/cache/` (skipping anything prefixed `_`, the
internal machinery) and looks for a module-level `caches` tuple. Any module
that defines one becomes a registered namespace automatically — adding a new
cache namespace means writing a new file with a `caches = (...)` tuple, not
editing a central registration list. This is why `account.py`, `crypto.py`,
and `sessions.py` are namespaces and `_registry.py`/`_locked_ttl.py` are not:
the leading underscore opts a module out of discovery.

---

## What's Actually Cached

| Namespace | Item | Key | TTL | Capacity |
|---|---|---|---|---|
| crypto | `current_linkage_key` | literal `"current"` | 30 min | 1 |
| crypto | `linkage_keys_by_version` | key version (int) | 30 min | 16 |
| crypto | `survey_keys` | `(project_id, survey_id)` | 10 min | 512 |
| crypto | `session_deks` | session UUID | 30 min | 10,000 |
| sessions | `write_context` | browser session token hash | 30 min | 10,000 |
| account | `email_verified` | Auth0 `sub` | 15 sec | 10,000 |

The `email_verified` TTL is worth noting as deliberately different in kind
from the others: 15 seconds isn't there to save a network call for a
meaningful stretch of time, it's there to collapse a burst of near-simultaneous
checks (multiple tabs, retry-after-refresh) into one live Auth0 lookup. The
database flag remains the actual source of truth; this cache is not a
substitute for it (see
[auth0-identity-and-email-verification.md](auth0-identity-and-email-verification.md)).

---

## Single-Flight Loading

`LockedTTLCache` (`cache/_locked_ttl.py`) wraps `cachetools.TTLCache` with two
locks: one global lock guarding the cache dict itself, and one per-key lock
used inside `get_or_load(key, loader)`. The per-key lock is what prevents a
thundering herd: if ten concurrent requests miss the same cache key at once,
only one of them actually calls `loader()` (the expensive KMS unwrap or DB
hit); the other nine block on that key's lock and then read the now-populated
value. Without this, a cold cache under concurrent load would fire the
expensive operation once per waiting request instead of once total.

The explicit reason this isn't `flask.g`: `g` is scoped to a single
request/app context and is discarded when that context ends, so it cannot
serve as a cross-request cache. `AppCache` is built once at app startup and
lives for the process's lifetime, shared across every request it handles.

---

## One Global Switch

Caching as a whole is gated by a single config flag,
`flowform.encryption.key_cache_enabled` (default `True`), read once at
`init_app(app)` and propagated down through every namespace to every
`LockedTTLCache.set_enabled()`. Disabling it clears all caches immediately.
There is no per-namespace or per-item flag — despite `email_verified` being a
conceptually different kind of cache from the crypto keys, one switch
controls both. Turning caching off falls through to whatever the loader does
on every call (KMS unwrap, live Auth0 check, etc.) — there's no hard
dependency on the cache being available, by design.

---

## Summary

| Concern | Mechanism |
| --- | --- |
| Registration | Auto-discovery of `caches` tuples in non-underscore modules under `app/cache/` |
| Isolation | Per-namespace grouping (`account`, `crypto`, `sessions`) |
| Concurrency | Global lock for dict access + per-key lock for single-flight loads |
| Lifetime | Built once at app startup, lives for the process — not `flask.g` |
| Kill switch | One config flag, `key_cache_enabled`, propagated to every item |

---

## Loose Threads

**No per-namespace or per-item enable/disable**, despite the namespace
structure suggesting that granularity was anticipated. All caching is on or
off together via the single global flag.

**Eviction beyond TTL/capacity relies entirely on `cachetools` defaults.**
There's no custom eviction policy — a namespace hitting its `maxsize` falls
back to whatever `cachetools.TTLCache`'s LRU behavior does, which is
reasonable but not something FlowForm-specific code has tuned per cache
item's actual access pattern.

**`session_deks` capacity (10,000) is a flat number, not derived from
expected concurrent session volume.** If concurrent in-progress sessions
regularly exceed that, this cache would be evicting and re-unwrapping DEKs
under normal load, not just under cache-cold conditions.
