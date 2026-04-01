# SQLAlchemy Constraint Rules

## Rule List

1. **Simple primary keys, foreign keys, and unique constraints are defined inline.**
   - Use inline definitions when the constraint applies to a single column and does not need extra semantic meaning.

2. **Composite primary keys, foreign keys, and unique constraints are defined as named table-level constraints.**
   - Use explicit `CONSTRAINT ...` names in SQL.
   - Use `PrimaryKeyConstraint(...)`, `ForeignKeyConstraint(...)`, or `UniqueConstraint(...)` in SQLAlchemy.

3. **All check constraints are explicitly named.**
   - This keeps validation errors readable.
   - This also makes migrations and schema diffs more stable.

4. **Use automatic naming conventions as the default fallback for simple inline constraints.**
   - This keeps the schema consistent without manually naming everything.

5. **Use manual names when the constraint expresses business meaning.**
   - Especially for composite foreign keys such as `same_project` or `same_survey` rules.

---

## Naming Convention

Use this SQLAlchemy metadata naming convention:

```python
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ix": "ix_%(column_0_label)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}
```

---

## How to Apply It

### Inline simple constraints

Examples:

```sql
id BIGSERIAL PRIMARY KEY,
project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
email TEXT NOT NULL UNIQUE
```

### Named composite constraints

Examples:

```sql
CONSTRAINT uq_response_stores_project_name
    UNIQUE (project_id, name)

CONSTRAINT fk_survey_submissions_store_same_project
    FOREIGN KEY (project_id, response_store_id)
    REFERENCES response_stores(project_id, id)
```

### Named check constraints

Examples:

```sql
CONSTRAINT ck_response_stores_store_type_valid
    CHECK (store_type IN ('platform_postgres', 'external_postgres'))

CONSTRAINT ck_response_stores_connection_reference_is_object
    CHECK (jsonb_typeof(connection_reference) = 'object')
```

---

## Practical Summary

- **Simple = inline**
- **Composite = named table-level constraint**
- **Checks = always named**
- **Automatic naming convention = default for simple constraints**
- **Manual naming = required when constraint meaning matters**

---

## Example: Project Memberships

```sql
CREATE TABLE project_memberships (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    role_id BIGINT REFERENCES project_roles(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_project_memberships_status_valid
        CHECK (status IN ('active', 'invited')),

    CONSTRAINT uq_project_memberships_user_project
        UNIQUE (user_id, project_id),

    CONSTRAINT uq_project_memberships_project_id_id
        UNIQUE (project_id, id),

    CONSTRAINT fk_project_memberships_role_same_project
        FOREIGN KEY (project_id, role_id)
        REFERENCES project_roles(project_id, id)
);
```

### Notes

- Simple FKs are defined inline (`user_id`, `project_id`, `role_id`)
- Composite FK is named because it enforces a domain rule (`same_project`)
- Composite uniques are named for clarity and FK support
- Check constraint is always named for readability and debugging
