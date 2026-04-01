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
    # pk_<table>
    "uq": "uq_%(table_name)s_%(column_0_name)s",  
    # uq_<table>_<column>
    "ix": "ix_%(table_name)s_%(column_0_name)s",  
    # ix_<table>_<column>
    "fk": "fk_%(table_name)s_%(column_0_name)s__%(referred_table_name)s",  
    # fk_<table>_<local_column>__<referred_table>
    "ck": "ck_%(table_name)s_%(constraint_name)s",  
    # ck_<table>_<explicit_constraint_name>
}
```

---

## How to Apply It

### Inline simple constraints

Examples:

```sql
id BIGSERIAL PRIMARY KEY,
project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
email TEXT NOT NULL UNIQUE,
created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL
```

With the naming convention, examples of generated names would be:

```text
pk_project_memberships
fk_project_memberships_project_id__projects
uq_users_email
fk_response_stores_created_by_user_id__users
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

These are manually named because they express composite structure or domain meaning.

### Named check constraints

Examples:

```sql
CONSTRAINT ck_response_stores_store_type_valid
    CHECK (store_type IN ('platform_postgres', 'external_postgres'))

CONSTRAINT ck_response_stores_connection_reference_is_object
    CHECK (jsonb_typeof(connection_reference) = 'object')
```

Check constraints should always be given an explicit semantic suffix, because the naming convention formats them as:

```text
ck_<table>_<explicit_constraint_name>
```

So a SQLAlchemy check name like:

```python
name="store_type_valid"
```

becomes:

```text
ck_response_stores_store_type_valid
```

---

## Practical Summary

- **Simple = inline**
- **Composite = named table-level constraint**
- **Checks = always named**
- **Automatic naming convention = default for simple constraints**
- \*\*Simple FK automatic format = \*\***`fk_<table>_<local_column>__<referred_table>`**
- \*\*Simple unique automatic format = \*\***`uq_<table>_<column>`**
- \*\*Simple primary key automatic format = \*\***`pk_<table>`**
- \*\*Check format = \*\***`ck_<table>_<explicit_constraint_name>`**
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
- If left automatic, those simple FK names would be:
  - `fk_project_memberships_user_id__users`
  - `fk_project_memberships_project_id__projects`
  - `fk_project_memberships_role_id__project_roles`
- Composite FK is named because it enforces a domain rule (`same_project`)
- Composite uniques are named for clarity and FK support
- Check constraint is always named for readability and debugging

---

## SQLAlchemy Model Example

```python
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProjectMembership(Base):
    """Associates a user with a project, optionally assigning a role."""

    __tablename__ = "project_memberships"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("project_roles.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('active', 'invited')", name="ck_project_memberships_status_valid"),
        UniqueConstraint("user_id", "project_id", name="uq_project_memberships_user_project"),
        UniqueConstraint("project_id", "id", name="uq_project_memberships_project_id_id"),
        ForeignKeyConstraint(
            ["project_id", "role_id"],
            ["project_roles.project_id", "project_roles.id"],
            name="fk_project_memberships_role_same_project",
        ),
    )

    user: Mapped[User] = relationship("User", foreign_keys=[user_id])
    project: Mapped[Project] = relationship("Project", foreign_keys=[project_id])
    role: Mapped[ProjectRole | None] = relationship("ProjectRole", foreign_keys=[role_id])
```
