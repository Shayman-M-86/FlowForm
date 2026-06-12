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

By default, the report is intentionally compact: it prints summary counts and
only hard failures. Use the output flags below when you need exploratory detail.

It checks four things:

1. DEAD RULES        — rule keys that match no DB constraint (the dangerous
                       case: a rule that can never fire).
2. TYPE MISMATCHES   — a rule whose matcher type (unique/fk/check) disagrees
                       with the constraint's actual type.
3. UNHANDLED RUNTIME — enforced constraints with no rule on tables that already
                       participate in integrity-error translation, excluding
                       low-level schema-shape guards and explicitly documented
                       intentional fallbacks. These are the constraints most
                       likely to surface as UNHANDLED_DB_INTEGRITY_ERROR.
4. UNMAPPED (info)   — enforced constraints with no rule that are not currently
                       classified as actionable. Advisory only.

It also annotates each matched constraint as inline-autonamed vs explicitly
named, so you can see which rule keys ride on Postgres auto-naming (and would
break if someone later names that constraint).

Usage
-----
    uv run python scripts/check_integrity_rule_constraints.py
    uv run python scripts/check_integrity_rule_constraints.py --keep   # leave container running
    uv run python scripts/check_integrity_rule_constraints.py --details
    uv run python scripts/check_integrity_rule_constraints.py --show-advisory
    uv run python scripts/check_integrity_rule_constraints.py --verbose

Requires Docker (spins up an ephemeral postgres:17) and the dev extras
(psycopg). Exit code is non-zero if any hard-failure category is found;
advisory constraints never fail the run.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import re
import secrets
import subprocess
import sys
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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

warnings.filterwarnings("ignore", message="authlib.jose module is deprecated.*")


@dataclass(frozen=True)
class DbConstraint:
    name: str
    contype: str  # u / f / c / p
    table: str
    definition: str = ""
    columns: tuple[str, ...] = ()
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
    table: str | None = None


@dataclass(frozen=True)
class RuntimeCoverageGap:
    constraint: DbConstraint
    contexts: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class ReportOptions:
    details: bool = False
    show_advisory: bool = False
    show_inline: bool = False
    show_messages: bool = False


# Constraints in this set are intentionally allowed to fall through if they
# somehow fire in the API path. Keep the list small: it exists for business-ish
# CHECKs that our generic "low-level schema guard" heuristics cannot safely
# classify. Every entry needs a short rationale because it is a conscious choice
# to not translate that DB error for clients.
INTENTIONALLY_UNMAPPED_CONSTRAINTS: dict[str, str] = {
    "ck_project_invitations_accepted_fields": "accepted_by/accepted_at are service-controlled state fields",
    "ck_subject_ip_observations_has_owner": "owner attachment is controlled by subject/session tracking services",
    "ck_submission_events_question_absent_for_session_events": "event shape is produced by server event code",
    "ck_submission_events_question_required_for_question_events": "event shape is produced by server event code",
    "ck_survey_links_used_at_requires_assignment": "used_at is only written by link-consumption service code",
    "ck_surveys_public_requires_slug": "survey visibility/public_slug is validated before persistence",
    "ck_surveys_slug_requires_public_visibility": "survey visibility/public_slug is validated before persistence",
}


LOW_LEVEL_CHECK_NAME_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"^ck_.*_(len|format|valid|is_object|positive|size)$",
        r"^ck_.*_(after|before)_.*$",
        r"^ck_.*_(consistent|present)$",
        r"^ck_.*_required_keys_present$",
    )
)


# --- ephemeral postgres --------------------------------------------------------


def _run(cmd: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kw)  # type: ignore[arg-type]


def start_postgres(port: int, password: str) -> str:
    name = f"flowform-rulecheck-{secrets.token_hex(4)}"
    res = _run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            "-e",
            f"POSTGRES_PASSWORD={password}",
            "-e",
            "POSTGRES_DB=flowform_check",
            "-p",
            f"127.0.0.1:{port}:5432",
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
            SELECT
                c.conname,
                c.contype,
                rel.relname,
                pg_get_constraintdef(c.oid, true) AS definition,
                COALESCE(
                    array_agg(att.attname ORDER BY cols.ordinality)
                        FILTER (WHERE att.attname IS NOT NULL),
                    ARRAY[]::text[]
                ) AS column_names
            FROM pg_constraint c
            JOIN pg_class rel ON rel.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = rel.relnamespace
            LEFT JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS cols(attnum, ordinality) ON true
            LEFT JOIN pg_attribute att ON att.attrelid = c.conrelid AND att.attnum = cols.attnum
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
            GROUP BY c.oid, c.conname, c.contype, rel.relname
            """
        ).fetchall()
        for conname, contype, relname, definition, column_names in rows:
            constraints[conname] = DbConstraint(
                name=conname,
                contype=contype,
                table=relname,
                definition=definition,
                columns=tuple(column_names or ()),
            )

        # Partial / expression UNIQUE indexes never appear in pg_constraint, but
        # integrity rules key off them (e.g. uq_survey_versions_one_published).
        idx_rows = conn.execute(
            """
            SELECT
                i.relname AS index_name,
                t.relname AS table_name,
                pg_get_indexdef(i.oid) AS definition,
                COALESCE(
                    array_agg(att.attname ORDER BY keys.ordinality)
                        FILTER (WHERE att.attname IS NOT NULL),
                    ARRAY[]::text[]
                ) AS column_names
            FROM pg_index x
            JOIN pg_class i ON i.oid = x.indexrelid
            JOIN pg_class t ON t.oid = x.indrelid
            JOIN pg_namespace n ON n.oid = i.relnamespace
            LEFT JOIN LATERAL unnest(x.indkey) WITH ORDINALITY AS keys(attnum, ordinality) ON true
            LEFT JOIN pg_attribute att ON att.attrelid = x.indrelid AND att.attnum = keys.attnum
            WHERE x.indisunique
              AND NOT x.indisprimary
              AND n.nspname NOT IN ('pg_catalog', 'information_schema')
            GROUP BY i.oid, i.relname, t.relname
            """
        ).fetchall()
        for index_name, table_name, definition, column_names in idx_rows:
            # Only add unique indexes that aren't already backed by a constraint.
            if index_name not in constraints:
                constraints[index_name] = DbConstraint(
                    name=index_name,
                    contype="u",
                    table=table_name,
                    definition=definition,
                    columns=tuple(column_names or ()),
                    is_unique_index=True,
                )
    return constraints


# --- rule extraction -----------------------------------------------------------


def _load_integrity_rules_module() -> Any:
    stderr = io.StringIO()
    with warnings.catch_warnings(), contextlib.redirect_stderr(stderr):
        warnings.filterwarnings("ignore", message=".*authlib\\.jose module is deprecated.*", category=Warning)
        import app.db.error_handling.integrity_rules as ir

    return ir


def fetch_rule_keys() -> list[RuleKey]:
    ir = _load_integrity_rules_module()

    out: list[RuleKey] = []
    for ctx, rules in ir.RULES_BY_CONTEXT.items():
        ctx_name = getattr(ctx, "__name__", str(ctx))
        ctx_table = getattr(ctx, "__tablename__", None)
        for rule in rules:
            matcher = DRIVER_ERROR_TO_MATCHER.get(rule.driver_error, "message")  # type: ignore[arg-type]
            out.append(RuleKey(key=rule.key, matcher=matcher, context=ctx_name, table=ctx_table))
    return out


def fetch_surface_fields() -> set[str]:
    ir = _load_integrity_rules_module()

    return set(ir.allowed_parameters)


# --- coverage classification ---------------------------------------------------


def _context_names_by_table(rules: list[RuleKey]) -> dict[str, tuple[str, ...]]:
    table_to_contexts: dict[str, set[str]] = {}
    for rule in rules:
        if rule.table is not None:
            table_to_contexts.setdefault(rule.table, set()).add(rule.context)
    return {table: tuple(sorted(contexts)) for table, contexts in table_to_contexts.items()}


def _is_low_level_check(constraint: DbConstraint) -> bool:
    return constraint.matcher == "check" and any(
        pattern.match(constraint.name) for pattern in LOW_LEVEL_CHECK_NAME_PATTERNS
    )


def _is_fk_support_unique(constraint: DbConstraint) -> bool:
    """Return true for UNIQUE constraints that exist mainly to support composite FKs."""
    if constraint.matcher != "unique" or constraint.is_unique_index:
        return False

    column_set = set(constraint.columns)
    return "id" in column_set and any(column.endswith("_id") for column in column_set if column != "id")


def _is_plain_inline_fk(constraint: DbConstraint) -> bool:
    """Inline FKs are usually ordinary existence checks, not custom app conflicts."""
    return constraint.matcher == "foreign_key" and constraint.is_inline_autonamed


def find_runtime_coverage_gaps(
    *,
    unmapped: list[DbConstraint],
    rules: list[RuleKey],
    surface_fields: set[str],
) -> list[RuntimeCoverageGap]:
    contexts_by_table = _context_names_by_table(rules)
    gaps: list[RuntimeCoverageGap] = []

    for constraint in unmapped:
        if constraint.table not in contexts_by_table:
            continue

        if constraint.name in INTENTIONALLY_UNMAPPED_CONSTRAINTS:
            continue

        if _is_fk_support_unique(constraint) or _is_plain_inline_fk(constraint) or _is_low_level_check(constraint):
            continue

        if constraint.columns and not (set(constraint.columns) & surface_fields):
            continue

        if constraint.matcher == "check":
            reason = "business-rule CHECK on a table with integrity-rule contexts"
        elif constraint.matcher == "foreign_key":
            reason = "named FK on a table with integrity-rule contexts"
        elif constraint.matcher == "unique":
            reason = "business UNIQUE/index on a table with integrity-rule contexts"
        else:
            reason = f"{constraint.matcher} constraint on a table with integrity-rule contexts"

        gaps.append(
            RuntimeCoverageGap(
                constraint=constraint,
                contexts=contexts_by_table[constraint.table],
                reason=reason,
            )
        )

    return sorted(
        gaps,
        key=lambda gap: (gap.constraint.table, gap.constraint.name),
    )


# --- reporting -----------------------------------------------------------------


def _constraint_ref(constraint: DbConstraint, *, include_details: bool) -> str:
    ref = f"{constraint.matcher} {constraint.table}.{constraint.name}"
    if include_details and constraint.columns:
        ref += f" columns={', '.join(constraint.columns)}"
    if include_details and constraint.definition:
        ref += f" — {constraint.definition}"
    return ref


def _rule_ref(rule: RuleKey) -> str:
    return f"[{rule.context}] {rule.matcher}_rule key={rule.key!r}"


def _print_section(title: str) -> None:
    print()
    print(title)


def report(constraints: dict[str, DbConstraint], rules: list[RuleKey], options: ReportOptions) -> int:
    surface_fields = fetch_surface_fields()
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
    runtime_gaps = find_runtime_coverage_gaps(unmapped=unmapped, rules=rules, surface_fields=surface_fields)
    runtime_gap_names = {gap.constraint.name for gap in runtime_gaps}
    advisory_unmapped = [c for c in unmapped if c.name not in runtime_gap_names]

    inline_matched = [
        (r, constraints[r.key])
        for r in constraint_rules
        if r.key in constraints and constraints[r.key].is_inline_autonamed
    ]

    failure_count = len(dead) + len(mismatched) + len(runtime_gaps)

    print("Integrity rule constraint check")
    print(
        f"  constraints={len(constraints)} | rules={len(rules)} "
        f"({len(constraint_rules)} constraint-keyed, {len(message_rules)} message-keyed)"
    )
    print(
        f"  hidden advisory={len(advisory_unmapped)} | inline-name warnings={len(inline_matched)} "
        f"| message rules={len(message_rules)}"
    )
    print("  optional output: --details, --show-advisory, --show-inline, --show-messages, --verbose")

    if failure_count:
        _print_section("Failures")
    else:
        _print_section("Failures")
        print("  none")

    if dead:
        print(f"  Dead rules ({len(dead)})")
        for rule in dead:
            print(f"    ✗ {_rule_ref(rule)}")

    if mismatched:
        print(f"  Type mismatches ({len(mismatched)})")
        for rule, constraint in mismatched:
            print(
                f"    ✗ [{rule.context}] key={rule.key!r}: "
                f"rule expects {rule.matcher}, DB has {constraint.matcher} (contype={constraint.contype})"
            )

    if runtime_gaps:
        print(f"  Missing runtime rules ({len(runtime_gaps)})")
        for gap in runtime_gaps:
            contexts = ", ".join(gap.contexts)
            print(f"    ✗ [{contexts}] {_constraint_ref(gap.constraint, include_details=options.details)}")
            if options.details:
                print(f"      reason: {gap.reason}")

    if options.show_advisory:
        _print_section(f"Advisory unmapped constraints ({len(advisory_unmapped)})")
        if not advisory_unmapped:
            print("  none")
        for constraint in advisory_unmapped:
            tag = " [inline-autonamed]" if constraint.is_inline_autonamed else ""
            intent = INTENTIONALLY_UNMAPPED_CONSTRAINTS.get(constraint.name)
            intent_note = f" — intentional: {intent}" if intent and options.details else ""
            print(f"  · {_constraint_ref(constraint, include_details=options.details)}{tag}{intent_note}")

    if options.show_inline:
        _print_section(f"Rules matching inline auto-named constraints ({len(inline_matched)})")
        if not inline_matched:
            print("  none")
        for rule, constraint in inline_matched:
            print(f"  ! [{rule.context}] key={rule.key!r} -> inline {constraint.table}.{constraint.name}")

    if options.show_messages:
        _print_section(f"Message rules ({len(message_rules)})")
        if not message_rules:
            print("  none")
        for rule in message_rules:
            message = rule.key if options.details else rule.key[:70]
            print(f"  ~ [{rule.context}] {message!r}")

    _print_section("Result")
    if failure_count:
        print(
            "FAIL — "
            f"{len(dead)} dead rule(s), "
            f"{len(mismatched)} type mismatch(es), "
            f"{len(runtime_gaps)} likely missing rule(s)."
        )
    else:
        print(
            "OK — every constraint-keyed rule matches a constraint of the right type, "
            "and no likely missing runtime rules were found."
        )
    print()
    return 1 if failure_count else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cross-check integrity_rules.py against real Postgres constraint names.",
        epilog=(
            "Default output prints only summary counts and hard failures. "
            "Use --details for constraint definitions, --show-advisory for hidden unmapped constraints, "
            "--show-inline for inline auto-name warnings, --show-messages for trigger/message rules, "
            "or --verbose for all optional output."
        ),
    )
    parser.add_argument("--keep", action="store_true", help="leave the postgres container running")
    parser.add_argument(
        "--details",
        action="store_true",
        help="include constraint columns/definitions and classification reasons",
    )
    parser.add_argument(
        "--show-advisory",
        action="store_true",
        help="list advisory unmapped constraints that do not fail the check",
    )
    parser.add_argument(
        "--show-inline",
        action="store_true",
        help="list rules that match inline auto-named constraints",
    )
    parser.add_argument(
        "--show-messages",
        action="store_true",
        help="list message-keyed rules that cannot be validated via pg_constraint",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="show all optional sections with detailed constraint output",
    )
    args = parser.parse_args()
    options = ReportOptions(
        details=args.details or args.verbose,
        show_advisory=args.show_advisory or args.verbose,
        show_inline=args.show_inline or args.verbose,
        show_messages=args.show_messages or args.verbose,
    )

    port = 5400 + secrets.randbelow(500)
    password = secrets.token_hex(16)
    dsn = f"host=127.0.0.1 port={port} user=postgres password={password} dbname=flowform_check"

    name = start_postgres(port, password)
    try:
        wait_ready(name, dsn)
        load_schema(dsn)
        constraints = fetch_constraints(dsn)
        rules = fetch_rule_keys()
        return report(constraints, rules, options)
    finally:
        if args.keep:
            print(f"\n(container {name} left running on port {port})")
        else:
            stop_postgres(name)


if __name__ == "__main__":
    raise SystemExit(main())
