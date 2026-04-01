from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest
from psycopg import Connection


def read_env(var_name: str, *, required: bool = True) -> str:
    value = os.getenv(var_name)
    if value is None:
        if required:
            pytest.fail(f"Expected environment variable {var_name!r} to be set.")
        return ""
    return value


def read_secret_file(env_name: str) -> str:
    secret_path = Path(read_env(env_name))

    if not secret_path.is_file():
        pytest.fail(f"Secret file from {env_name!r} does not exist: {secret_path}")

    return secret_path.read_text(encoding="utf-8").strip()


def connect_for_prefix(prefix: str) -> Connection:
    host = read_env(f"{prefix}_HOST")
    port = int(read_env(f"{prefix}_PORT"))
    dbname = read_env(f"{prefix}_NAME")
    user = read_env(f"{prefix}_APP_USER")
    password = read_secret_file(f"{prefix}_APP_PASSWORD_FILE")
    return psycopg.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    )


def current_database_name(prefix: str) -> str:
    with connect_for_prefix(prefix) as conn, conn.cursor() as cur:
        cur.execute("SELECT current_database()")
        row = cur.fetchone()

    if row is None:
        pytest.fail(f"No database name returned for {prefix}")

    return str(row[0])
