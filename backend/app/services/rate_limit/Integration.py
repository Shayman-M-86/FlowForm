from __future__ import annotations

import logging
from typing import Callable

from flask import Flask, request

from app.services.rate_limit.service import RateLimitService, RateLimitConfig
from app.utils.general import get_client_ip
from app.core.config import Settings
from app.core.responses import error_response

logger = logging.getLogger(__name__)





def rate_limiting(
    app: Flask,
    service: RateLimitService,
    *,
    ip_getter: Callable[[], str] = get_client_ip,
) -> None:
    if app.extensions.get("rate_limiting_registered"):
        return

    app.extensions["rate_limiter"] = service

    @app.before_request
    def enforce_rate_limit():
        if service.is_ignored_path(request.path):
            return None

        ip = ip_getter()
        decision = service.check(ip)

        if decision.allowed:
            return None


        response, status_code = error_response(
            "Too many requests. Please try again later.",
            error_code="rate_limit_exceeded",
            status_code=429,
        )

        if decision.retry_after_seconds is not None:
            response.headers["Retry-After"] = str(decision.retry_after_seconds)

        return response, status_code

    app.extensions["rate_limiting_registered"] = True


def register_rate_limiting(app: Flask, settings: Settings):
    if settings.rate_limit.enabled:
        max_requests = settings.rate_limit.max_requests
        window_seconds = settings.rate_limit.window_seconds
        ignored_paths = settings.rate_limit.ignored_paths

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

