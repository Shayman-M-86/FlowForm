
import logging

from flask import request, g

def to_bool(value: str) -> bool:
    return value.lower() in {"true", "1", "yes", "on"}

def get_client_ip() -> str:
    if hasattr(g, "client_ip"):
        return g.client_ip

    xff = request.headers.get("X-Forwarded-For")
    if xff:
        ip = xff.partition(",")[0].strip()
    else:
        ip = request.remote_addr or "unknown"

    g.client_ip = ip
    return ip

def get_log_level(status_code: int) -> int:
    if status_code >= 500:
        return logging.ERROR
    if status_code >= 400:
        return logging.WARNING
    if status_code >= 300:
        return logging.INFO
    return logging.DEBUG

