"""Account cache definitions."""

from __future__ import annotations

from typing import Protocol

from app.cache._item import CacheItem
from app.cache._spec import CacheSpec

# Keyed by auth0_user_id. Short TTL: this smooths out repeated checks from
# the same user/tab within a few seconds (e.g. refresh spam, multiple tabs
# polling, or a user mashing "check verification") -- it is not a source of
# truth. users.email_verified in the database remains authoritative; a cache
# miss always falls through to a live Auth0 lookup.
email_verified: CacheSpec[str, bool] = CacheSpec(
    attr="email_verified",
    maxsize=10_000,
    ttl_seconds=15,
)

caches = (email_verified,)


class AccountCacheNamespace(Protocol):
    """Typed account cache namespace exposed by the app cache registry."""

    email_verified: CacheItem[str, bool]
