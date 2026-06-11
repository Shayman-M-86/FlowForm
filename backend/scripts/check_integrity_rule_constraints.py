#!/usr/bin/env python
"""Cross-check integrity_rules.py against the real database constraint names.

Why this exists
---------------
``app/db/error_handling/integrity_rules.py`` translates Postgres constraint
violations into ``AppError`` instances. Each rule matches on a *constraint
name* (or, for ``message_rule``, a trigger message). The names it matches are
the ones Postgres reports at runtime (``exc.orig.diag.constraint_name``) — and
the real database is built from the SQL schema files, never from ORM metadata.

That makes the rule keys silently coupled to the SQL schema. If a constraint is
renamed, removed, or an inline constraint's auto-generated name shifts, the
matching rule goes *dead*: the violation falls through to a generic 500 instead
of the intended 409, with no error at import time and no test failure unless a
test happens to exercise that exact path.

This script closes that gap. It loads the schema into a throwaway Postgres,
reads the *actual* constraint names from ``pg_constraint`` (authoritative —
including inline auto-named constraints, truncation, and collision suffixes),
and cross-references them against the rule keys.

It reports three things:

1. DEAD RULES        — rule keys that match no DB constraint (the dangerous
                       case: a rule that can never fire).
2. TYPE MISMATCHES   — a rule whose matcher type (unique/fk/check) disagrees
                       with the constraint's actual type.
3. UNMAPPED (info)   — enforced constraints with no rule. Advisory only: most
                       CHECKs deliberately have no rule (they should 500). This
                       list is where you'd spot a RESTRICT FK or UNIQUE whose
                       violation is currently an ugly 500 you might want to map.

It also annotates each matched constraint as inline-autonamed vs explicitly
named, so you can see which rule keys ride on Postgres auto-naming (and would
break if someone later names that constraint).

Usage
-----
    uv run python scripts/check_integrity_rule_constraints.py
    uv run python scripts/check_integrity_rule_constraints.py --keep   # leave container running

Requires Docker (spins up an ephemeral postgres:17) and the dev extras
(psycopg). Exit code is non-zero if any DEAD RULES or TYPE MISMATCHES are found;
UNMAPPED constraints never fail the run.
"""

from __future__ import annotations

import argparse
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation

# --- locate schema files relative to this script -------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
# Make ``app`` importable regardless of the invoking cwd.
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCHEMA_DIR = REPO_ROOT / "infra" / "postgres" / "init" / "schema"
SCHEMA_FILES = (
    SCHEMA_DIR / "flowform_core_db_schema_v4.sql",
    SCHEMA_DIR / "flowform_response_db_schema_v4.sql",
)

PG_IMAGE = "postgres:17"

# pg_constraint.contype -> the matcher we expect a rule to use for it.
# 'p' (primary key) is introspected for completeness but never has a rule.
CONTYPE_TO_MATCHER = {
    "u": "unique",  # also covers unique indexes, handled separately below
    "f": "foreign_key",
    "c": "check",
    "p": "primary_key",
}

DRIVER_ERROR_TO_MATCHER = {
    UniqueViolation: "unique",
    ForeignKeyViolation: "foreign_key",
    CheckViolation: "check",
}


@dataclass(frozen=True)
class DbConstraint:
    name: str
    contype: str  # u / f / c / p
    table: str
    is_unique_index: bool = False  # partial/expression unique indexes (not in pg_constraint)

    @property
    def matcher(self) -> str:
        if self.is_unique_index:
            return "unique"
        return CONTYPE_TO_MATCHER.get(self.contype, "unknown")

    @property
    def is_inline_autonamed(self) -> bool:
        """Heuristic: Postgres auto-names inline constraints <table>_<col>_<suffix>.

        Explicit names in this codebase use the uq_/fk_/ck_/pk_ prefixes, so a
        name carrying a trailing _key/_fkey/_pkey and *not* a convention prefix
        is almost certainly an inline auto-name. Used only for annotation.
        """
        if self.name.startswith(("uq_", "fk_", "ck_", "pk_", "ix_")):
            return False
        return self.name.endswith(("_key", "_fkey", "_pkey")) or "_key" in self.name


@dataclass(frozen=True)
class RuleKey:
    key: str
    matcher: str  # unique / foreign_key / check / message
    context: str  # ORM class name, for reporting


# --- ephemeral postgres --------------------------------------------------------


def _run(cmd: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kw)  # type: ignore[arg-type]


def start_postgres(port: int, password: str) -> str:
    name = f"flowform-rulecheck-{secrets.token_hex(4)}"
    res = _run(
        [
            "docker", "run", "-d", "--rm",
            "--name", name,
            "-e", f"POSTGRES_PASSWORD={password}",
            "-e", "POSTGRES_DB=flowform_check",
            "-p", f"127.0.0.1:{port}:5432",
            PG_IMAGE,
        ]
    )
    if res.returncode != 0:
        sys.exit(f"Failed to start postgres container:\n{res.stderr}")
    return name


def wait_ready(name: str, dsn: str, timeout: float = 60.0) -> None:
    """Wait until a real host connection succeeds.

    pg_isready inside the container reports ready during the image's init phase,
    before Postgres restarts for its final start — so probing from the host with
    an actual connection is the only reliable readiness signal.
    """
    deadline = time.monotonic() + timeout
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        # Bail early if the container died (e.g. schema-independent startup error).
        if _run(["docker", "ps", "-q", "--filter", f"name={name}"]).stdout.strip() == "":
            logs = _run(["docker", "logs", name]).stderr or _run(["docker", "logs", name]).stdout
            sys.exit(f"Postgres container exited during startup:\n{logs[-2000:]}")
        try:
            with psycopg.connect(dsn, connect_timeout=2):
                return
        except psycopg.OperationalError as exc:
            last_err = exc
            time.sleep(0.5)
    sys.exit(f"Postgres did not become ready in time. Last error:\n{last_err}")


def stop_postgres(name: str) -> None:
    _run(["docker", "stop", name])


def load_schema(dsn: str) -> None:
    with psycopg.connect(dsn, autocommit=True) as conn:
        for sql_file in SCHEMA_FILES:
            if not sql_file.exists():
                sys.exit(f"Schema file not found: {sql_file}")
            sql = sql_file.read_text()
            try:
                conn.execute(sql)  # type: ignore[arg-type]
            except psycopg.Error as exc:
                sys.exit(f"Error loading {sql_file.name}: {exc}")


# --- introspection -------------------------------------------------------------


def fetch_constraints(dsn: str) -> dict[str, DbConstraint]:
    constraints: dict[str, DbConstraint] = {}
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            """
            SELECT c.conname, c.contype, rel.relname
            FROM pg_constraint c
            JOIN pg_class rel ON rel.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = rel.relnamespace
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
            """
        ).fetchall()
        for conname, contype, relname in rows:
            constraints[conname] = DbConstraint(name=conname, contype=contype, table=relname)

        # Partial / expression UNIQUE indexes never appear in pg_constraint, but
        # integrity rules key off them (e.g. uq_survey_versions_one_published).
        idx_rows = conn.execute(
            """
            SELECT i.relname AS index_name, t.relname AS table_name
            FROM pg_index x
            JOIN pg_class i ON i.oid = x.indexrelid
            JOIN pg_class t ON t.oid = x.indrelid
            JOIN pg_namespace n ON n.oid = i.relnamespace
            WHERE x.indisunique
              AND NOT x.indisprimary
              AND n.nspname NOT IN ('pg_catalog', 'information_schema')
            """
        ).fetchall()
        for index_name, table_name in idx_rows:
            # Only add unique indexes that aren't already backed by a constraint.
            if index_name not in constraints:
                constraints[index_name] = DbConstraint(
                    name=index_name, contype="u", table=table_name, is_unique_index=True
                )
    return constraints


# --- rule extraction -----------------------------------------------------------


def fetch_rule_keys() -> list[RuleKey]:
    import app.db.error_handling.integrity_rules as ir

    out: list[RuleKey] = []
    for ctx, rules in ir.RULES_BY_CONTEXT.items():
        ctx_name = getattr(ctx, "__name__", str(ctx))
        for rule in rules:
            matcher = DRIVER_ERROR_TO_MATCHER.get(rule.driver_error, "message")  # type: ignore[arg-type]
            out.append(RuleKey(key=rule.key, matcher=matcher, context=ctx_name))
    return out


# --- reporting -----------------------------------------------------------------


def report(constraints: dict[str, DbConstraint], rules: list[RuleKey]) -> int:
    constraint_rules = [r for r in rules if r.matcher != "message"]
    message_rules = [r for r in rules if r.matcher == "message"]

    dead: list[RuleKey] = []
    mismatched: list[tuple[RuleKey, DbConstraint]] = []
    matched_names: set[str] = set()

    for r in constraint_rules:
        con = constraints.get(r.key)
        if con is None:
            dead.append(r)
            continue
        matched_names.add(con.name)
        if con.matcher != r.matcher:
            mismatched.append((r, con))

    unmapped = sorted(
        (c for c in constraints.values() if c.contype != "p" and c.name not in matched_names),
        key=lambda c: (c.table, c.name),
    )

    print(f"\nIntrospected {len(constraints)} constraints; {len(rules)} rules "
          f"({len(constraint_rules)} constraint-keyed, {len(message_rules)} message-keyed).\n")

    # 1. DEAD RULES (hard failure)
    print("\n")
    print("1. DEAD RULES — rule key matches no DB constraint (rule can never fire)")
    print("\n")
    if not dead:
        print("  none ✓")
    else:
        for r in dead:
            print(f"  ✗ [{r.context}] {r.matcher}_rule key={r.key!r}")

    # 2. TYPE MISMATCHES (hard failure)
    print("\n")
    print("2. TYPE MISMATCHES — rule matcher disagrees with constraint type")
    print("\n")
    if not mismatched:
        print("  none ✓")
    else:
        for r, con in mismatched:
            print(f"  ✗ [{r.context}] key={r.key!r}: rule expects {r.matcher}, "
                  f"DB has {con.matcher} (contype={con.contype})")

    # 3. UNMAPPED (advisory)
    print("\n")
    print("3. UNMAPPED CONSTRAINTS (advisory — most CHECKs intentionally 500)")
    print("\n")
    if not unmapped:
        print("  none")
    else:
        for c in unmapped:
            tag = " [inline-autonamed]" if c.is_inline_autonamed else ""
            print(f"  · {c.matcher:12} {c.table}.{c.name}{tag}")

    # Annotation: matched rules riding on inline auto-names (tripwire)
    inline_matched = [
        (r, constraints[r.key])
        for r in constraint_rules
        if r.key in constraints and constraints[r.key].is_inline_autonamed
    ]
    print("\n")
    print("4. RULES MATCHING INLINE AUTO-NAMED CONSTRAINTS (would break if renamed)")
    print("\n")
    if not inline_matched:
        print("  none")
    else:
        for r, con in inline_matched:
            print(f"  ! [{r.context}] key={r.key!r} -> inline {con.table}.{con.name}")

    # message_rules can't be validated against pg_constraint; list for awareness.
    print("\n")
    print("5. MESSAGE RULES (matched by trigger text, not constraint name — not checked)")
    print("\n")
    for r in message_rules:
        print(f"  ~ [{r.context}] {r.key[:70]!r}")

    failures = len(dead) + len(mismatched)
    print("\n")
    if failures:
        print(f"RESULT: FAIL — {len(dead)} dead rule(s), {len(mismatched)} type mismatch(es).")
    else:
        print("RESULT: OK — every constraint-keyed rule matches a constraint of the right type.")
    print("\n")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true", help="leave the postgres container running")
    args = parser.parse_args()

    port = 5400 + secrets.randbelow(500)
    password = secrets.token_hex(16)
    dsn = f"host=127.0.0.1 port={port} user=postgres password={password} dbname=flowform_check"

    name = start_postgres(port, password)
    try:
        wait_ready(name, dsn)
        load_schema(dsn)
        constraints = fetch_constraints(dsn)
        rules = fetch_rule_keys()
        return report(constraints, rules)
    finally:
        if args.keep:
            print(f"\n(container {name} left running on port {port})")
        else:
            stop_postgres(name)


if __name__ == "__main__":
    raise SystemExit(main())
