"""Jinja template rendering for email content."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateError,
    TemplateNotFound,
    select_autoescape,
)

from app.email_service.exceptions import (
    EmailRenderError,
    EmailTemplateNotFoundError,
)


class EmailRenderer:
    """Render email templates using Jinja.

    This class has no Flask dependency.
    """

    def __init__(self, template_dir: Path | None = None) -> None:
        self.template_dir = template_dir or Path(__file__).parent / "templates"

        self.environment = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a single template with the given context."""
        try:
            template = self.environment.get_template(template_name)
            return template.render(**context)

        except TemplateNotFound as exc:
            raise EmailTemplateNotFoundError(
                f"Email template not found: {template_name}"
            ) from exc

        except TemplateError as exc:
            raise EmailRenderError(
                f"Failed to render email template: {template_name}"
            ) from exc

    def render_html_and_text(
        self,
        *,
        template_base_name: str,
        context: dict[str, Any],
    ) -> tuple[str, str]:
        """Render matching HTML and plain-text templates.

        Example:
            template_base_name='survey_invite'

        Renders:
            survey_invite.html
            survey_invite.txt
        """
        html_body = self.render(f"{template_base_name}.html", context)
        text_body = self.render(f"{template_base_name}.txt", context)

        return html_body, text_body