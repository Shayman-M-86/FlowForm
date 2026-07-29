# TODO(migration): Update paths, contracts, and runtime wiring for infra-new before this file is used.
"""Idempotent PostgreSQL reconciliation and verification."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from psycopg import Connection, sql

from .models import (
    DATABASES,
    BootstrapPhase,
    BootstrapRequest,
    DatabaseDefinition,
)
from .services import PostgresConnector, SqlRepository

LOGGER = logging.getLogger()
ADVISORY_LOCK_ID = 6_631_746_337_671_109


def _requires_schema_load(
    existing_tables: frozenset[str],
    expected_tables: frozenset[str],
    database_name: str,
) -> bool:
    if not existing_tables:
        return True
    if existing_tables != expected_tables:
        raise RuntimeError(f"Database schema is neither empty nor the expected baseline for {database_name}.")
    return False


class PostgresBootstrapper:
    """Reconciles and verifies the logical RDS structure and baseline schemas."""

    def __init__(
        self,
        connector: PostgresConnector,
        scripts: SqlRepository,
    ) -> None:
        self._connector = connector
        self._scripts = scripts
        self.phase = BootstrapPhase.CONNECT

    def run(self, request: BootstrapRequest) -> None:
        """Apply every idempotent bootstrap phase under one advisory lock."""
        with (
            self._connector.connect("postgres", autocommit=True) as control,
            self._advisory_lock(control),
        ):
            self.phase = BootstrapPhase.METADATA_CHECK
            self._ensure_metadata_table(control)
            self._assert_version_checksum(control, request)

            self.phase = BootstrapPhase.ROLES
            with control.transaction():
                control.execute(sql.SQL(self._scripts.read("roles_v1.sql")))

            self.phase = BootstrapPhase.DATABASES
            self._ensure_databases(control)
            self._configure_database_access(control)

            self.phase = BootstrapPhase.DATABASE_CONFIGURATION
            for database in DATABASES:
                self._configure_database(database)

            self.phase = BootstrapPhase.VERIFICATION
            self._verify_cluster(control)
            for database in DATABASES:
                self._verify_database(database)

            self.phase = BootstrapPhase.RECORD_VERSION
            self._record_version(control, request)

        self.phase = BootstrapPhase.COMPLETE

    @contextmanager
    def _advisory_lock(
        self,
        connection: Connection[Any],
    ) -> Iterator[None]:
        connection.execute(
            "SELECT pg_advisory_lock(%s)",
            (ADVISORY_LOCK_ID,),
        )
        try:
            yield
        finally:
            try:
                connection.execute(
                    "SELECT pg_advisory_unlock(%s)",
                    (ADVISORY_LOCK_ID,),
                )
            except Exception:
                LOGGER.warning("Database bootstrap advisory-lock cleanup failed.")

    @staticmethod
    def _ensure_metadata_table(connection: Connection[Any]) -> None:
        with connection.transaction():
            connection.execute("CREATE SCHEMA IF NOT EXISTS flowform_system")
            connection.execute("REVOKE ALL ON SCHEMA flowform_system FROM PUBLIC")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS flowform_system.bootstrap_history (
                    bootstrap_version text PRIMARY KEY,
                    script_checksum text NOT NULL,
                    applied_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            connection.execute("REVOKE ALL ON flowform_system.bootstrap_history FROM PUBLIC")

    @staticmethod
    def _assert_version_checksum(
        connection: Connection[Any],
        request: BootstrapRequest,
    ) -> None:
        row = connection.execute(
            """
            SELECT script_checksum
            FROM flowform_system.bootstrap_history
            WHERE bootstrap_version = %s
            """,
            (request.version,),
        ).fetchone()
        if row and row[0] != request.checksum:
            raise ValueError("Bootstrap version already exists with a different checksum.")

    @staticmethod
    def _ensure_databases(connection: Connection[Any]) -> None:
        database_names = [database.name for database in DATABASES]
        existing = {
            row[0]
            for row in connection.execute(
                "SELECT datname FROM pg_database WHERE datname = ANY(%s)",
                (database_names,),
            ).fetchall()
        }
        for database in DATABASES:
            if database.name not in existing:
                connection.execute(
                    sql.SQL("CREATE DATABASE {} OWNER flowform_owner").format(sql.Identifier(database.name))
                )

    @staticmethod
    def _configure_database_access(connection: Connection[Any]) -> None:
        for database in DATABASES:
            database_name = sql.Identifier(database.name)
            application_role = sql.Identifier(database.application_role)
            connection.execute(sql.SQL("ALTER DATABASE {} OWNER TO flowform_owner").format(database_name))
            connection.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(database_name))
            for candidate in DATABASES:
                connection.execute(
                    sql.SQL("REVOKE CONNECT ON DATABASE {} FROM {}").format(
                        database_name,
                        sql.Identifier(candidate.application_role),
                    )
                )
            connection.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO flowform_migrator").format(database_name))
            connection.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    database_name,
                    application_role,
                )
            )

    def _configure_database(self, database: DatabaseDefinition) -> None:
        expected_tables = self._scripts.schema_table_names(database.schema_script)
        with self._connector.connect(
            database.name,
            autocommit=True,
        ) as connection:
            with connection.transaction():
                connection.execute(sql.SQL(self._scripts.read(database.setup_script)))

            existing_tables = self._database_table_names(
                connection,
                database.schema_name,
            )
            if _requires_schema_load(
                existing_tables,
                expected_tables,
                database.name,
            ):
                with connection.transaction():
                    connection.execute("SET LOCAL ROLE flowform_owner")
                    connection.execute(
                        sql.SQL("SET LOCAL search_path TO {}, public").format(sql.Identifier(database.schema_name))
                    )
                    connection.execute(sql.SQL(self._scripts.read_schema(database.schema_script)))

            # Reapply current-object grants after the first schema load. Default
            # privileges in the same script cover objects created by migrations.
            with connection.transaction():
                connection.execute(sql.SQL(self._scripts.read(database.setup_script)))

    @staticmethod
    def _database_table_names(
        connection: Connection[Any],
        schema_name: str,
    ) -> frozenset[str]:
        return frozenset(
            row[0]
            for row in connection.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = %s
                """,
                (schema_name,),
            ).fetchall()
        )

    def _verify_cluster(self, connection: Connection[Any]) -> None:
        cursor = connection.execute(sql.SQL(self._scripts.read("verification_v1.sql")))
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Cluster verification failed: no_result.")
        check_names = [column.name for column in cursor.description or ()]
        failed_checks = [
            check_name for check_name, succeeded in zip(check_names, row, strict=True) if succeeded is not True
        ]
        if failed_checks:
            raise RuntimeError(f"Cluster verification failed: {','.join(failed_checks)}.")

    def _verify_database(self, database: DatabaseDefinition) -> None:
        expected_tables = self._scripts.schema_table_names(database.schema_script)
        other_application_role = next(
            candidate.application_role
            for candidate in DATABASES
            if candidate.application_role != database.application_role
        )
        with self._connector.connect(
            database.name,
            autocommit=True,
        ) as connection:
            table_rows = connection.execute(
                """
                SELECT tablename, tableowner
                FROM pg_tables
                WHERE schemaname = %s
                """,
                (database.schema_name,),
            ).fetchall()
            actual_tables = {row[0]: row[1] for row in table_rows}
            if set(actual_tables) != expected_tables:
                raise RuntimeError(f"Application table verification failed for {database.name}.")
            if any(owner != "flowform_owner" for owner in actual_tables.values()):
                raise RuntimeError(f"Application table ownership verification failed for {database.name}.")

            row = connection.execute(
                """
                SELECT
                    pg_get_userbyid(nspowner) = 'flowform_owner'
                    AND has_schema_privilege(%s, %s, 'USAGE')
                    AND NOT has_schema_privilege(%s, %s, 'USAGE')
                    AND NOT EXISTS (
                        SELECT 1
                        FROM aclexplode(
                            COALESCE(nspacl, acldefault('n', nspowner))
                        ) acl
                        WHERE acl.grantee = 0
                          AND acl.privilege_type IN ('USAGE', 'CREATE')
                    )
                FROM pg_namespace
                WHERE nspname = %s
                """,
                (
                    database.application_role,
                    database.schema_name,
                    other_application_role,
                    database.schema_name,
                    database.schema_name,
                ),
            ).fetchone()
            if not row or row[0] is not True:
                raise RuntimeError(f"Database configuration verification failed for {database.name}.")

            table_privileges_valid = connection.execute(
                """
                SELECT bool_and(
                    has_table_privilege(
                        %s,
                        format('%%I.%%I', schemaname, tablename),
                        'SELECT, INSERT, UPDATE, DELETE'
                    )
                )
                FROM pg_tables
                WHERE schemaname = %s
                """,
                (database.application_role, database.schema_name),
            ).fetchone()
            if not table_privileges_valid or table_privileges_valid[0] is not True:
                raise RuntimeError(f"Application table privilege verification failed for {database.name}.")

            sequence_privileges_valid = connection.execute(
                """
                SELECT count(*) = 0 OR bool_and(
                    has_sequence_privilege(
                        %s,
                        format('%%I.%%I', schemaname, sequencename),
                        'USAGE, SELECT'
                    )
                )
                FROM pg_sequences
                WHERE schemaname = %s
                """,
                (database.application_role, database.schema_name),
            ).fetchone()
            if not sequence_privileges_valid or sequence_privileges_valid[0] is not True:
                raise RuntimeError(f"Application sequence privilege verification failed for {database.name}.")

    @staticmethod
    def _record_version(
        connection: Connection[Any],
        request: BootstrapRequest,
    ) -> None:
        with connection.transaction():
            connection.execute(
                """
                INSERT INTO flowform_system.bootstrap_history
                    (bootstrap_version, script_checksum)
                VALUES (%s, %s)
                ON CONFLICT (bootstrap_version) DO NOTHING
                """,
                (request.version, request.checksum),
            )
