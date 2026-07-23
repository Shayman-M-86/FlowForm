import logging
from collections.abc import Iterable
from ipaddress import ip_address, ip_network

from flask import request


def to_bool(value: str) -> bool:
    """Return True if a string represents a truthy value."""
    return value.lower() in {"true", "1", "yes", "on"}


def get_client_ip(*, trusted_proxy_cidrs: Iterable[str] = ()) -> str:
    """Return the socket peer, or a forwarded address from a trusted proxy only."""
    peer = request.remote_addr or "unknown"
    trusted_networks = tuple(ip_network(cidr, strict=False) for cidr in trusted_proxy_cidrs)

    try:
        peer_address = ip_address(peer)
        peer_is_trusted = any(peer_address in network for network in trusted_networks)
    except ValueError:
        peer_is_trusted = False

    if peer_is_trusted:
        forwarded = request.headers.get("X-Forwarded-For", "").partition(",")[0].strip()
        if forwarded:
            return forwarded
    return peer


def get_log_level(status_code: int) -> int:
    """Map an HTTP status code to an appropriate logging level.

    Successful (2xx) and redirect (3xx) responses log at INFO so completed
    requests are visible at the default INFO root level in every environment.
    Previously 2xx logged at DEBUG, so under gunicorn (prod/rehearsal) — which,
    unlike the Flask dev server, emits no werkzeug access line — successful
    requests produced no log at all. Client errors escalate to WARNING and
    server errors to ERROR.
    """
    if status_code >= 500:
        return logging.ERROR
    if status_code >= 400:
        return logging.WARNING
    return logging.INFO
