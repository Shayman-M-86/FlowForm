import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase

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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_project_subjects_project_id_id"),
        UniqueConstraint("project_id", "subject_code", name="uq_project_subjects_project_id_subject_code"),
        CheckConstraint(
            "subject_code = btrim(subject_code) AND char_length(subject_code) BETWEEN 1 AND 128",
            name="subject_code_len",
        ),
    )

    project: Mapped[Project] = relationship("Project", foreign_keys=[project_id])
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
    identity_type: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    normalized_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(Text, server_default=text("'unverified'"), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "project_subject_id"],
            ["project_subjects.project_id", "project_subjects.id"],
            ondelete="CASCADE",
            name="fk_project_subject_identities_subject_same_project",
        ),
        CheckConstraint(
            "identity_type IN ('email', 'authenticated_user')",
            name="identity_type_valid",
        ),
        CheckConstraint(
            "(identity_type = 'email' AND normalized_email IS NOT NULL AND user_id IS NULL)"
            " OR (identity_type = 'authenticated_user' AND user_id IS NOT NULL AND normalized_email IS NULL)",
            name="identity_value_valid",
        ),
        CheckConstraint(
            "verification_status IN ('unverified', 'verified')",
            name="verification_status_valid",
        ),
        CheckConstraint(
            "(verification_status = 'verified') = (verified_at IS NOT NULL)",
            name="verified_at_consistent",
        ),
        CheckConstraint(
            "normalized_email IS NULL"
            " OR (normalized_email = lower(btrim(normalized_email))"
            " AND char_length(normalized_email) BETWEEN 3 AND 320)",
            name="normalized_email_valid",
        ),
        CheckConstraint(
            "verified_at IS NULL OR verified_at >= attached_at",
            name="verified_at_after_attached_at",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= attached_at",
            name="revoked_at_after_attached_at",
        ),
        Index(
            "uq_project_subject_identities_active_user",
            "project_id",
            "user_id",
            unique=True,
            postgresql_where=text(
                "identity_type = 'authenticated_user' AND user_id IS NOT NULL AND revoked_at IS NULL"
            ),
        ),
        Index(
            "uq_project_subject_identities_subject_active_email",
            "project_subject_id",
            "normalized_email",
            unique=True,
            postgresql_where=text(
                "identity_type = 'email' AND normalized_email IS NOT NULL AND revoked_at IS NULL"
            ),
        ),
        Index(
            "uq_project_subject_identities_project_verified_email",
            "project_id",
            "normalized_email",
            unique=True,
            postgresql_where=text(
                "identity_type = 'email' AND normalized_email IS NOT NULL"
                " AND verification_status = 'verified' AND revoked_at IS NULL"
            ),
        ),
        Index(
            "ix_project_subject_identities_subject",
            "project_subject_id",
        ),
        Index(
            "ix_project_subject_identities_user",
            "user_id",
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index(
            "ix_project_subject_identities_email",
            "normalized_email",
            postgresql_where=text("normalized_email IS NOT NULL"),
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
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "project_subject_id"],
            ["project_subjects.project_id", "project_subjects.id"],
            ondelete="CASCADE",
            name="fk_project_subject_tokens_subject_same_project",
        ),
        CheckConstraint(
            "token_hash ~ '^[0-9a-f]{64}$'",
            name="token_hash_format",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="expires_at_after_created_at",
        ),
        CheckConstraint(
            "last_used_at IS NULL OR last_used_at >= created_at",
            name="last_used_at_after_created_at",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="revoked_at_after_created_at",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR last_used_at IS NULL OR last_used_at <= revoked_at",
            name="last_used_before_revocation",
        ),
        Index(
            "ix_project_subject_tokens_subject",
            "project_subject_id",
        ),
        Index(
            "ix_project_subject_tokens_active_expiry",
            "expires_at",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    subject: Mapped[ProjectSubject] = relationship(
        "ProjectSubject",
        foreign_keys=[project_id, project_subject_id],
        back_populates="tokens",
        overlaps="project",
    )
