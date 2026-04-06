from __future__ import annotations

import logging
from collections.abc import Callable

from flask import Flask, request

from app.core.config import Settings
from app.core.errors import RateLimitExceededError
from app.middleware.rate_limit.service import RateLimitConfig, RateLimitService
from app.utils.general import get_client_ip

logger = logging.getLogger(__name__)

def rate_limiting(
    app: Flask,
    service: RateLimitService,
    *,
    ip_getter: Callable[[], str] = get_client_ip,
) -> None:
    """Register rate limiting middleware on a Flask app.

    Args:
        app: Flask application instance.
        service: Rate limiting service used to evaluate requests.
        ip_getter: Callable that returns the client IP address.
    """
    if app.extensions.get("rate_limiting_registered"):
        return

    app.extensions["rate_limiter"] = service

    logger.debug("Registering rate limiting middleware")
    @app.before_request
    def enforce_rate_limit():
        if service.is_ignored_path(request.path):
            return None

        ip = ip_getter()
        decision = service.check(ip)

        if decision.allowed:
            return None

        raise RateLimitExceededError



    app.extensions["rate_limiting_registered"] = True


def register_rate_limiting(app: Flask, settings: Settings):
    """Configure and register rate limiting based on application settings.

    Args:
        app: Flask application instance.
        settings: Application settings containing rate limit config.
    """
    if settings.flowform.rate_limit.enabled:
        max_requests = settings.flowform.rate_limit.max_requests
        window_seconds = settings.flowform.rate_limit.window_seconds
        ignored_paths = settings.flowform.rate_limit.ignored_paths

        logger.info(
            "Enabling rate limiting: max_requests=%d, window_seconds=%d, ignored_paths=%s",
            max_requests,
            window_seconds,
            ignored_paths,
        )

        rate_limit_service = RateLimitService(
            RateLimitConfig(
                max_requests=max_requests,
                window_seconds=window_seconds,
                ignored_paths=set(ignored_paths),
            )
        )
        rate_limiting(app, rate_limit_service)

