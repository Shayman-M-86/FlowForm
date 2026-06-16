from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase
from app.schema.enums import SubjectIdentityType, SubjectIdentityVerificationStatus

if TYPE_CHECKING:
    from app.schema.orm.core.project import Project
    from app.schema.orm.core.user import User


class ProjectSubject(CoreBase):
    """Stable project-scoped participant record.

    Identities, recognition tokens, links, sessions, and IP observations attach
    around it.
    """

    __tablename__ = "project_subjects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    subject_code: Mapped[str] = mapped_column(Text, nullable=False)

    # Null = this is the canonical subject.
    # Set = this subject is an alias pointing to the canonical subject.
    canonical_subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_project_subjects_project_id_id"),
        ForeignKeyConstraint(
            ["project_id", "canonical_subject_id"],
            ["project_subjects.project_id", "project_subjects.id"],
            name="fk_project_subjects_canonical_subject",
            ondelete="RESTRICT",
        ),
    )

    project: Mapped[Project] = relationship("Project", foreign_keys=[project_id])

    canonical_subject: Mapped[ProjectSubject | None] = relationship(
        "ProjectSubject",
        foreign_keys=[project_id, canonical_subject_id],
        remote_side=[project_id, id],
        viewonly=True,
    )

    aliases: Mapped[list[ProjectSubject]] = relationship(
        "ProjectSubject",
        foreign_keys=[project_id, canonical_subject_id],
        viewonly=True,
    )

    identities: Mapped[list[ProjectSubjectIdentity]] = relationship(
        "ProjectSubjectIdentity",
        foreign_keys="ProjectSubjectIdentity.project_subject_id",
        back_populates="subject",
        viewonly=True,
    )

    tokens: Mapped[list[ProjectSubjectToken]] = relationship(
        "ProjectSubjectToken",
        foreign_keys="ProjectSubjectToken.project_subject_id",
        back_populates="subject",
        viewonly=True,
    )


class ProjectSubjectIdentity(CoreBase):
    """A revocable email or authenticated-user identity attached to a subject."""

    __tablename__ = "project_subject_identities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    project_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    identity_type: Mapped[SubjectIdentityType] = mapped_column(Text, nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    normalized_email: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[SubjectIdentityVerificationStatus] = mapped_column(
        Text, server_default=text("'unverified'"), nullable=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (
        # Composite UNIQUE that project_participants' identity FK targets, proving
        # an identity belongs to a subject within the same project.
        UniqueConstraint(
            "project_id",
            "project_subject_id",
            "id",
            name="uq_project_subject_identities_project_subject_id",
        ),
        ForeignKeyConstraint(
            ["project_id", "project_subject_id"],
            ["project_subjects.project_id", "project_subjects.id"],
            ondelete="CASCADE",
            name="fk_project_subject_identities_subject_same_project",
        ),
        ForeignKeyConstraint(
            ["user_id", "normalized_email"],
            ["users.id", "users.email"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_project_subject_identities_user_email_matches",
        ),
    )

    subject: Mapped[ProjectSubject] = relationship(
        "ProjectSubject",
        foreign_keys=[project_id, project_subject_id],
        back_populates="identities",
        overlaps="project",
    )
    user: Mapped[User | None] = relationship("User", foreign_keys=[user_id])


class ProjectSubjectToken(CoreBase):
    """Reusable recognition-token hash reconnecting a browser to a stable subject.

    Spans surveys in one project. token_hash is a lowercase hex SHA-256 digest;
    the raw token is never stored.
    """

    __tablename__ = "project_subject_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    project_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "project_subject_id"],
            ["project_subjects.project_id", "project_subjects.id"],
            ondelete="CASCADE",
            name="fk_project_subject_tokens_subject_same_project",
        ),
    )

    subject: Mapped[ProjectSubject] = relationship(
        "ProjectSubject",
        foreign_keys=[project_id, project_subject_id],
        back_populates="tokens",
        overlaps="project",
    )
