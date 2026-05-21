"""Auth0 Device Authorization Flow for the FlowForm dev MCP.

Same UX as the GitHub CLI: print a URL, the user logs in once in their
browser, the CLI polls Auth0 until the user finishes, then caches token
metadata to disk and stores the tokens in the OS credential store.

Subsequent runs reuse the cached access token. When it expires, the refresh
token is exchanged silently. If refresh fails (revoked, refresh token
expired), we fall back to re-running the device flow.

Token cache location: ``~/.config/flowform/token.json`` (override via
``FLOWFORM_TOKEN_PATH``). Tokens are encrypted with AES-GCM before they are
written to that file, avoiding Linux keyring prompts during MCP startup.

Required env (set in tools/mcp/.env):

    FLOWFORM_AUTH0_DOMAIN     e.g. flowform.eu.auth0.com
    FLOWFORM_AUTH0_CLIENT_ID  Auth0 application client_id (SPA or Native)
    FLOWFORM_AUTH0_AUDIENCE   API audience identifier
    FLOWFORM_TOKEN_ENCRYPTION_KEY  base64:<32 random bytes, base64-encoded>
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _is_wsl() -> bool:
    """Detect WSL so we can route browser-open through the Windows host."""
    if sys.platform != "linux":
        return False
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def _open_browser(url: str) -> None:
    """Open URL in the user's default browser.

    On WSL, falls through to the Windows host's default browser via
    ``cmd.exe /c start`` — the Linux ``webbrowser`` module otherwise grabs
    whatever happens to be on PATH (often a graphical text editor) and the
    result doesn't render properly.

    Override entirely with FLOWFORM_BROWSER_CMD to specify a custom command;
    ``{url}`` in the value is replaced with the verification URL.
    """
    override = os.environ.get("FLOWFORM_BROWSER_CMD")
    if override:
        cmd = override.replace("{url}", url) if "{url}" in override else f"{override} {url}"
        try:
            subprocess.Popen(cmd, shell=True)
            return
        except OSError as exc:
            print(f"[flowform-mcp] FLOWFORM_BROWSER_CMD failed: {exc}", file=sys.stderr)

    if _is_wsl():
        cmd_exe = shutil.which("cmd.exe") or "/mnt/c/Windows/System32/cmd.exe"
        try:
            # `start ""` requires the empty title to avoid swallowing the URL.
            subprocess.Popen([cmd_exe, "/c", "start", "", url])
            return
        except OSError as exc:
            print(
                f"[flowform-mcp] Could not launch Windows browser via cmd.exe ({exc}); "
                "falling back to the Linux webbrowser module.",
                file=sys.stderr,
            )

    try:
        webbrowser.open(url)
    except webbrowser.Error:
        pass


SCOPE = "openid profile email offline_access"
# Treat tokens as expired this many seconds before their stated expiry so we
# never hand the backend a token that's about to die mid-request.
EXPIRY_SLACK_SECONDS = 60
ACCESS_TOKEN_KEY = "access_token"
REFRESH_TOKEN_KEY = "refresh_token"
TOKEN_ENCRYPTION_KEY_ENV = "FLOWFORM_TOKEN_ENCRYPTION_KEY"
ENCRYPTED_SECRET_PREFIX = "flowform:aesgcm:v1:"


def _token_path() -> Path:
    override = os.environ.get("FLOWFORM_TOKEN_PATH")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "flowform" / "token.json"


def _secret_aad(cfg: "Auth0Config", key: str) -> str:
    return f"{cfg.domain}|{cfg.client_id}|{cfg.audience}|{key}"


def _encryption_key() -> bytes:
    value = _require_env(TOKEN_ENCRYPTION_KEY_ENV)

    if value.startswith("base64:"):
        encoded = value.removeprefix("base64:")
        try:
            key = base64.urlsafe_b64decode(encoded)
        except (ValueError, binascii.Error) as exc:
            print(
                f"[flowform-mcp] {TOKEN_ENCRYPTION_KEY_ENV} is not valid base64.",
                file=sys.stderr,
            )
            raise SystemExit(9) from exc
        if len(key) != 32:
            print(
                f"[flowform-mcp] {TOKEN_ENCRYPTION_KEY_ENV} must decode to 32 bytes.",
                file=sys.stderr,
            )
            raise SystemExit(9)
        return key

    return hashlib.sha256(value.encode()).digest()


def _encrypt_secret(cfg: "Auth0Config", key: str, value: str) -> str:
    account = _secret_aad(cfg, key).encode()
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_encryption_key()).encrypt(nonce, value.encode(), account)
    return (
        ENCRYPTED_SECRET_PREFIX
        + base64.urlsafe_b64encode(nonce).decode()
        + ":"
        + base64.urlsafe_b64encode(ciphertext).decode()
    )


def _decrypt_secret(cfg: "Auth0Config", key: str, value: str) -> str:
    if not value.startswith(ENCRYPTED_SECRET_PREFIX):
        return value

    encrypted = value.removeprefix(ENCRYPTED_SECRET_PREFIX)
    try:
        nonce_text, ciphertext_text = encrypted.split(":", 1)
        nonce = base64.urlsafe_b64decode(nonce_text)
        ciphertext = base64.urlsafe_b64decode(ciphertext_text)
        account = _secret_aad(cfg, key).encode()
        return AESGCM(_encryption_key()).decrypt(nonce, ciphertext, account).decode()
    except (ValueError, UnicodeDecodeError, binascii.Error, InvalidTag) as exc:
        print(
            f"[flowform-mcp] Could not decrypt cached token. Check {TOKEN_ENCRYPTION_KEY_ENV}.",
            file=sys.stderr,
        )
        raise SystemExit(9) from exc


def _read_cached_file() -> dict[str, Any] | None:
    path = _token_path()
    if not path.exists():
        return None
    try:
        cached = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(cached, dict):
        return None
    return cached


def _get_secret(cfg: "Auth0Config", key: str, cached: dict[str, Any] | None = None) -> str | None:
    source = cached if cached is not None else _read_cached_file()
    if not source:
        return None
    stored = source.get(key)
    if not isinstance(stored, str):
        return None
    return _decrypt_secret(cfg, key, stored)


def _set_secret(cfg: "Auth0Config", key: str, value: str) -> None:
    cached = _read_cached_file() or {}
    cached[key] = _encrypt_secret(cfg, key, value)
    _save_cached(cached)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(
            f"[flowform-mcp] Missing required env var: {name}. "
            "Set it in tools/mcp/.env.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return value


@dataclass
class Auth0Config:
    domain: str
    client_id: str
    audience: str

    @property
    def device_code_url(self) -> str:
        return f"https://{self.domain}/oauth/device/code"

    @property
    def token_url(self) -> str:
        return f"https://{self.domain}/oauth/token"

    @classmethod
    def from_env(cls) -> "Auth0Config":
        return cls(
            domain=_require_env("FLOWFORM_AUTH0_DOMAIN"),
            client_id=_require_env("FLOWFORM_AUTH0_CLIENT_ID"),
            audience=_require_env("FLOWFORM_AUTH0_AUDIENCE"),
        )


def _load_cached(cfg: Auth0Config) -> dict[str, Any] | None:
    cached = _read_cached_file()
    if cached is None:
        return None

    changed = False
    for key in (ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY):
        value = cached.get(key)
        if isinstance(value, str) and not value.startswith(ENCRYPTED_SECRET_PREFIX):
            cached[key] = _encrypt_secret(cfg, key, value)
            changed = True
    if changed:
        _save_cached(cached)

    return cached


def _save_cached(data: dict[str, Any]) -> None:
    path = _token_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    path.write_text(json.dumps(data, indent=2))
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _is_fresh(cached: dict[str, Any]) -> bool:
    expires_at = cached.get("expires_at")
    if not isinstance(expires_at, (int, float)):
        return False
    return time.time() < expires_at - EXPIRY_SLACK_SECONDS


def _store_tokens(
    cfg: Auth0Config,
    payload: dict[str, Any],
) -> dict[str, Any]:
    expires_in = int(payload.get("expires_in", 0))
    cached = _load_cached(cfg) or {}
    refresh_token = payload.get("refresh_token") or _get_secret(cfg, REFRESH_TOKEN_KEY, cached)
    if refresh_token:
        cached[REFRESH_TOKEN_KEY] = _encrypt_secret(cfg, REFRESH_TOKEN_KEY, refresh_token)

    stored = {
        ACCESS_TOKEN_KEY: _encrypt_secret(cfg, ACCESS_TOKEN_KEY, payload["access_token"]),
        "expires_at": time.time() + expires_in,
        "token_type": payload.get("token_type", "Bearer"),
        "scope": payload.get("scope"),
        "storage": "encrypted_file",
        "encryption": "aesgcm",
    }
    if refresh_token:
        stored[REFRESH_TOKEN_KEY] = cached[REFRESH_TOKEN_KEY]
    _save_cached(stored)
    return {**stored, "access_token": payload["access_token"], "refresh_token": refresh_token}


def _device_authorize(cfg: Auth0Config) -> dict[str, Any]:
    response = httpx.post(
        cfg.device_code_url,
        data={
            "client_id": cfg.client_id,
            "scope": SCOPE,
            "audience": cfg.audience,
        },
        timeout=10.0,
    )
    if response.status_code >= 400:
        try:
            body = response.json()
        except json.JSONDecodeError:
            body = {"raw": response.text}
        print(
            f"[flowform-mcp] Auth0 rejected the device authorization request "
            f"(HTTP {response.status_code}).",
            file=sys.stderr,
        )
        print(f"[flowform-mcp] Auth0 response: {body}", file=sys.stderr)
        print(
            f"[flowform-mcp] Request was: domain={cfg.domain} "
            f"client_id={cfg.client_id} audience={cfg.audience} scope={SCOPE!r}",
            file=sys.stderr,
        )
        print(
            "[flowform-mcp] Common causes:\n"
            "  - Device Code grant not enabled on the Auth0 application\n"
            "  - The Auth0 application is not authorized for this API audience\n"
            "  - The audience value is wrong (must match an API identifier exactly)\n"
            "  - The client_id is for a SPA app (Device Code requires Native)",
            file=sys.stderr,
        )
        raise SystemExit(3)
    return response.json()


def _poll_for_token(cfg: Auth0Config, device_code: str, interval: int) -> dict[str, Any]:
    """Poll Auth0 until the user completes login (or it expires)."""
    while True:
        response = httpx.post(
            cfg.token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
                "client_id": cfg.client_id,
            },
            timeout=10.0,
        )
        if response.status_code == 200:
            return response.json()

        try:
            body = response.json()
        except json.JSONDecodeError:
            body = {}
        error = body.get("error")

        if error == "authorization_pending":
            time.sleep(interval)
            continue
        if error == "slow_down":
            interval += 5
            time.sleep(interval)
            continue
        if error == "expired_token":
            print(
                "[flowform-mcp] Device code expired before login completed. "
                "Run again to start a new login.",
                file=sys.stderr,
            )
            raise SystemExit(4)
        if error == "access_denied":
            print("[flowform-mcp] Login was denied.", file=sys.stderr)
            raise SystemExit(5)

        print(
            f"[flowform-mcp] Unexpected token endpoint response "
            f"({response.status_code}): {body}",
            file=sys.stderr,
        )
        raise SystemExit(6)


def _run_device_flow(cfg: Auth0Config) -> dict[str, Any]:
    auth = _device_authorize(cfg)
    verification_uri = auth.get("verification_uri_complete") or auth["verification_uri"]
    user_code = auth["user_code"]
    interval = int(auth.get("interval", 5))

    print("[flowform-mcp] Opening your browser to log in...", file=sys.stderr)
    print(f"[flowform-mcp] URL:       {verification_uri}", file=sys.stderr)
    print(f"[flowform-mcp] User code: {user_code}", file=sys.stderr)
    print(
        "[flowform-mcp] If the browser doesn't open, paste the URL above "
        "manually. Confirm the user code matches.",
        file=sys.stderr,
    )
    _open_browser(verification_uri)

    tokens = _poll_for_token(cfg, auth["device_code"], interval)
    print("[flowform-mcp] Login complete. Token cached.", file=sys.stderr)
    return _store_tokens(cfg, tokens)


def _refresh(cfg: Auth0Config, cached: dict[str, Any]) -> dict[str, Any] | None:
    refresh_token = _get_secret(cfg, REFRESH_TOKEN_KEY, cached)
    if not refresh_token:
        return None
    response = httpx.post(
        cfg.token_url,
        data={
            "grant_type": "refresh_token",
            "client_id": cfg.client_id,
            "refresh_token": refresh_token,
        },
        timeout=10.0,
    )
    if response.status_code != 200:
        return None
    return _store_tokens(cfg, response.json())


def get_access_token(*, force_login: bool = False) -> str:
    """Return a valid access token, refreshing or logging in as needed."""
    cfg = Auth0Config.from_env()

    if not force_login:
        cached = _load_cached(cfg)
        if cached and _is_fresh(cached):
            access_token = _get_secret(cfg, ACCESS_TOKEN_KEY, cached)
            if access_token:
                return access_token
        if cached:
            refreshed = _refresh(cfg, cached)
            if refreshed:
                return refreshed["access_token"]

    return _run_device_flow(cfg)["access_token"]


def login_cli() -> None:
    """Entry point for `python auth.py login` (and run.sh login)."""
    token = get_access_token(force_login=True)
    # Print the metadata path, not the token itself, to stderr/stdout.
    print(
        f"[flowform-mcp] Cached token metadata at {_token_path()}",
        file=sys.stderr,
    )
    # Output a marker so the calling shell can confirm success.
    print("ok", end="")
    if not token:
        raise SystemExit(7)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "login":
        login_cli()
    else:
        print("Usage: python auth.py login", file=sys.stderr)
        raise SystemExit(2)
