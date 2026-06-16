"""Orchestrate access resolution, subject resolution, and submission session creation.

Entry point for all session-start flows (public slug, general link, private link,
authenticated link). Resolves the survey and access grant, determines the final
ProjectSubject, applies merge and identity writes, issues or rotates the recognition
token, creates the session row, and consumes single-use links — all in one transaction.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain import survey_rules
from app.repositories import public_link_repo as plr
from app.repositories.core import project_subject_identities as sub_id
from app.repositories.core import project_subjects as subjects
from app.repositories.core import submission_sessions as ssr
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.api.responses.submission_sessions import PublicSubmissionSessionResponses
from app.schema.orm.core.user import User
from app.services.public_submissions.core.access_resolver import AccessResolver
from app.services.public_submissions.core.subject_resolver import SubjectResolver
from app.services.public_submissions.core.subject_token import SubjectTokenService


class SessionStarter:
    """Orchestrate a respondent session start end-to-end.

    Sequence:
      1. AccessResolver  → SubmissionAccessGrant   (which survey, which link, visibility check)
      2. SubjectTokenService.lookup               (browser recognition token candidate — read-only)
      3. SubjectResolver → SubjectResolutionResult (final subject + token/merge instructions)
      4. Apply merge writes (canonical_subject_id) if instructed
      5. Apply identity writes if instructed (create or attach identity for logged-in user)
      6. Apply token mechanics (issue / rotate / mark_used / keep)
      7. DB write: create submission session row, consume single-use link
      8. Commit, then return session response + raw recognition token

    No access or subject policy lives here — this class only orchestrates.
    """

    def __init__(
        self,
        *,
        access_resolver: AccessResolver | None = None,
        subject_resolver: SubjectResolver | None = None,
        token_service: SubjectTokenService | None = None,
    ) -> None:
        self._token_service = token_service or SubjectTokenService()
        self._access_resolver = access_resolver or AccessResolver()
        self._subject_resolver = subject_resolver or SubjectResolver(token_service=self._token_service)

    def start(
        self,
        db: Session,
        *,
        payload: StartSubmissionSessionRequest,
        actor: User | None,
        recognition_token: str | None = None,
    ) -> tuple[PublicSubmissionSessionResponses, str, str | None]:
        """Run the full session-start sequence.

        Returns (session_response, raw_browser_session_token, raw_recognition_token).
        raw_recognition_token is None when token_action is "none".
        """
        access = self._access_resolver.resolve(db, payload=payload, actor=actor)
        response_store_id = survey_rules.ensure_has_response_store(survey=access.survey)

        # Lookup recognition token candidate — does not update last_used_at.
        lookup = self._token_service.lookup(
            db, project_id=access.project_id, raw_token=recognition_token
        ) if recognition_token else None

        token_subject_id = lookup.token_subject_id if (lookup and lookup.token_valid) else None
        canonical_token_subject_id = lookup.canonical_token_subject_id if (lookup and lookup.token_valid) else None

        resolution = self._subject_resolver.resolve(
            db,
            project_id=access.project_id,
            access_method=access.access_method,
            assigned_subject_id=access.assigned_subject_id,
            token_subject_id=token_subject_id,
            canonical_token_subject_id=canonical_token_subject_id,
            actor_user_id=actor.id if actor is not None else None,
        )

        final_subject_id = resolution.final_subject_id

        # Apply canonical merge before anything else touches the subjects.
        if resolution.merge_subject_id is not None and resolution.merge_into_subject_id is not None:
            weaker = subjects.get_subject(
                db, project_id=access.project_id, subject_id=resolution.merge_subject_id
            )
            stronger = subjects.get_subject(
                db, project_id=access.project_id, subject_id=resolution.merge_into_subject_id
            )
            if weaker is not None and stronger is not None:
                subjects.set_canonical_subject(db, subject=weaker, canonical=stronger)

        # Write identity row when resolver determined one is needed.
        if actor is not None and resolution.needs_identity_write:
            sub_id.create_user_identity(
                db,
                project_id=access.project_id,
                project_subject_id=final_subject_id,
                user=actor,
            )

        # Apply token mechanics.
        raw_recognition_token: str | None = self._token_service.apply_token_action(
            db,
            project_id=access.project_id,
            final_subject_id=final_subject_id,
            token_action=resolution.token_action,
            existing_raw_token=recognition_token,
        )

        raw_browser_session_token = ssr.generate_browser_session_token()
        session = ssr.create_session(
            db,
            project_id=access.project_id,
            survey_id=access.survey_id,
            survey_version_id=access.survey_version_id,
            response_store_id=response_store_id,
            link_id=access.link_id,
            project_subject_id=final_subject_id,
            raw_browser_session_token=raw_browser_session_token,
        )

        if access.link is not None and access.is_single_use:
            plr.mark_used(db, link=access.link)

        commit_contexts = [session, access.link] if (access.link is not None and access.is_single_use) else [session]
        commit_with_err_handle(db, contexts=commit_contexts)

        # Public slug returns the survey schema with the session start response.
        # Link-based paths return the schema at pre-session link resolve time.
        survey_schema = (
            access.published_version.compiled_schema
            if access.access_method == "public_slug"
            else None
        )
        response = PublicSubmissionSessionResponses(
            status=session.session_status,
            started_at=session.started_at,
            expires_at=session.expires_at,
            survey_version_id=access.survey_version_id,
            survey_schema=survey_schema,
        )
        return response, raw_browser_session_token, raw_recognition_token
