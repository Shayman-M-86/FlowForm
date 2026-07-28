-- AWS/RDS cluster verification packaged by DatabaseBootstrapStack.

SELECT
    EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'flowform_owner'
          AND NOT rolcanlogin
          AND NOT rolsuper
    ) AS owner_role_valid,
    EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'flowform_migrator'
          AND rolcanlogin
    ) AS migrator_role_valid,
    EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'flowform_core_app'
          AND rolcanlogin
    ) AS core_role_valid,
    EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'flowform_response_app'
          AND rolcanlogin
    ) AS response_role_valid,
    (
        pg_has_role('flowform_migrator', 'rds_iam', 'member')
        AND pg_has_role('flowform_core_app', 'rds_iam', 'member')
        AND pg_has_role('flowform_response_app', 'rds_iam', 'member')
    ) AS rds_iam_membership_valid,
    NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = ANY (
            ARRAY[
                'flowform_owner',
                'flowform_migrator',
                'flowform_core_app',
                'flowform_response_app'
            ]
        )
          AND (
              rolsuper
              OR rolcreatedb
              OR rolcreaterole
              OR rolreplication
              OR rolbypassrls
          )
    ) AS role_privileges_valid,
    (
        has_database_privilege('flowform_migrator', 'flowform_core', 'CONNECT')
        AND has_database_privilege('flowform_migrator', 'flowform_response', 'CONNECT')
        AND has_database_privilege('flowform_core_app', 'flowform_core', 'CONNECT')
        AND NOT has_database_privilege(
            'flowform_core_app',
            'flowform_response',
            'CONNECT'
        )
        AND has_database_privilege(
            'flowform_response_app',
            'flowform_response',
            'CONNECT'
        )
        AND NOT has_database_privilege(
            'flowform_response_app',
            'flowform_core',
            'CONNECT'
        )
    ) AS database_connect_valid,
    (
        EXISTS (
            SELECT 1
            FROM pg_database
            WHERE datname = 'flowform_core'
              AND pg_get_userbyid(datdba) = 'flowform_owner'
        )
        AND EXISTS (
            SELECT 1
            FROM pg_database
            WHERE datname = 'flowform_response'
              AND pg_get_userbyid(datdba) = 'flowform_owner'
        )
    ) AS database_ownership_valid,
    NOT EXISTS (
        SELECT 1
        FROM pg_database database,
             aclexplode(COALESCE(database.datacl, acldefault('d', database.datdba))) acl
        WHERE database.datname IN ('flowform_core', 'flowform_response')
          AND acl.grantee = 0
          AND acl.privilege_type = 'CONNECT'
    ) AS public_connect_revoked;
