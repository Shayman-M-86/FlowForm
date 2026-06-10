"""Temporary compatibility import for the response-infrastructure rework."""

from app.schema.orm.core.project_subject import ProjectSubject

# TEMP(rework): Legacy imports still ask for ResponseSubjectMapping while the
# subject identity model is being replaced by ProjectSubject.
# Remove this alias after services/tests import ProjectSubject directly.
ResponseSubjectMapping = ProjectSubject

__all__ = ["ResponseSubjectMapping"]
