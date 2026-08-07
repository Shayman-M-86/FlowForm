"""Publication validation for survey definitions.

Pydantic answers whether a definition is safe, bounded and internally consistent.
This package answers whether its document-wide references and identities are coherent.
"""

from app.domain.surveys.publication.issues import PublicationIssue
from app.domain.surveys.publication.validator import ensure_publishable, validate_for_publication

__all__ = ["PublicationIssue", "ensure_publishable", "validate_for_publication"]
