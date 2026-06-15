from uuid import UUID

from sqlalchemy.orm import Session

from app.db.error_handling import RuleContext, commit_with_err_handle
from app.domain.errors import (
    ParticipantIdentityEmailMismatchError,
    ParticipantIdentityNotVerifiableError,
    ParticipantIdentityUserMismatchError,
    ParticipantNotFoundError,
)
from app.domain.guards import ensure_present
from app.repositories.core import project_participants as ppr
from app.repositories.core import project_subject_identities as pir
from app.repositories.core import project_subjects as psr
from app.schema.api.requests.participants import CreateParticipantRequest, UpdateParticipantRequest
from app.schema.orm.core.project_participant import ProjectParticipant
from app.schema.orm.core.project_subject import ProjectSubjectIdentity
from app.schema.orm.core.user import User


class ParticipantService:
    """Service for project participant operations.

    A participant always bundles three core rows: a project subject, an
    email-type subject identity, and the participant row linking them. Create
    makes all three; update re-points the email identity; delete removes all
    three (blocked with a conflict if a survey link still assigns the
    participant).
    """

    def list_participants(
        self,
        db: Session,
        *,
        project_id: int,
    ) -> list[ProjectParticipant]:
        return ppr.list_participants(db, project_id=project_id)

    def get_participant(
        self,
        db: Session,
        *,
        project_id: int,
        participant_id: UUID,
    ) -> ProjectParticipant:
        return ensure_present(
            ppr.get_participant(db, project_id=project_id, participant_id=participant_id),
            error=ParticipantNotFoundError(),
        )

    def create_participant(
        self,
        db: Session,
        *,
        project_id: int,
        data: CreateParticipantRequest,
    ) -> ProjectParticipant:
        """Create a subject, an email identity for it, and the participant row."""
        subject = psr.create_subject(db, project_id=project_id, subject_code=data.subject_code)
        identity = pir.create_email_identity(
            db,
            project_id=project_id,
            project_subject_id=subject.id,
            normalized_email=str(data.email),
        )
        participant = ppr.create_participant(
            db,
            project_id=project_id,
            project_subject_id=subject.id,
            identity_id=identity.id,
        )
        commit_with_err_handle(db, contexts=[subject, identity, participant])
        return participant

    def update_participant(
        self,
        db: Session,
        *,
        project_id: int,
        participant_id: UUID,
        data: UpdateParticipantRequest,
    ) -> ProjectParticipant:
        """Update the participant's email identity and/or subject code."""
        participant = self.get_participant(db, project_id=project_id, participant_id=participant_id)
        contexts: list[RuleContext] = [participant]

        if data.email is not None:
            identity = self._get_identity(db, project_id=project_id, participant=participant)
            pir.set_normalized_email(db, identity=identity, normalized_email=str(data.email))
            contexts.append(identity)

        if data.subject_code is not None:
            subject = ensure_present(
                psr.get_subject(db, project_id=project_id, subject_id=participant.project_subject_id),
                error=ParticipantNotFoundError(),
            )
            psr.set_subject_code(db, subject=subject, subject_code=data.subject_code)
            contexts.append(subject)

        commit_with_err_handle(db, contexts=contexts)
        return participant

    def delete_participant(
        self,
        db: Session,
        *,
        project_id: int,
        participant_id: UUID,
    ) -> None:
        """Delete the participant, its email identity, and its subject.

        The participant is removed first; an assigning survey link blocks it via
        ON DELETE RESTRICT, surfaced as a conflict by the integrity-rules layer.
        """
        participant = self.get_participant(db, project_id=project_id, participant_id=participant_id)
        identity = self._get_identity(db, project_id=project_id, participant=participant)
        subject = ensure_present(
            psr.get_subject(db, project_id=project_id, subject_id=participant.project_subject_id),
            error=ParticipantNotFoundError(),
        )

        ppr.delete_participant(db, participant=participant)
        pir.delete_identity(db, identity=identity)
        psr.delete_subject(db, subject=subject)
        commit_with_err_handle(db, contexts=[participant, identity, subject])

    def verify_participant_for_user(
        self,
        db: Session,
        *,
        participant: ProjectParticipant,
        user: User,
    ) -> ProjectParticipant:
        """Link a participant's email identity to a user with the same email.

        This is intentionally strict: the authenticated user's account email is
        the only proof used to upgrade the participant identity.
        """
        identity = self._get_identity(db, project_id=participant.project_id, participant=participant)

        if identity.identity_type == "authenticated_user":
            if identity.user_id == user.id:
                return participant
            raise ParticipantIdentityUserMismatchError()

        if identity.identity_type != "email" or identity.normalized_email is None:
            raise ParticipantIdentityNotVerifiableError()

        if self._normalize_email(user.email) != self._normalize_email(identity.normalized_email):
            raise ParticipantIdentityEmailMismatchError()

        pir.link_email_identity_to_user(db, identity=identity, user=user)
        commit_with_err_handle(db, contexts=[identity])
        return participant

    def _get_identity(
        self,
        db: Session,
        *,
        project_id: int,
        participant: ProjectParticipant,
    ) -> ProjectSubjectIdentity:
        return ensure_present(
            pir.get_identity(
                db,
                project_id=project_id,
                project_subject_id=participant.project_subject_id,
                identity_id=participant.identity_id,
            ),
            error=ParticipantNotFoundError(),
        )

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()
