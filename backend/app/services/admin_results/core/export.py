"""Export serialization for admin results.

Pure serialization: flatten session result trees into rows, then render those
rows as a CSV or JSON file body. No DB or crypto.
"""

from __future__ import annotations

import csv
import io
import json

from app.schema.enums import ExportFormat
from app.services.results import ExportFile, ExportRow, SessionTreeResult

_EXPORT_FIELDNAMES = [
    "session_id",
    "status",
    "started_at",
    "completed_at",
    "question_key",
    "answer_family",
    "has_encrypted_answer",
    "decrypted",
    "answer_state",
    "answer_value",
]


def to_export_rows(result: SessionTreeResult) -> list[ExportRow]:
    """Flatten one session's result into export rows, one per answer slot."""
    session = result.session
    if not result.answers:
        return [
            ExportRow(
                session_id=session.id,
                status=session.session_status,
                started_at=session.started_at,
                completed_at=session.completed_at,
            )
        ]
    return [
        ExportRow(
            session_id=session.id,
            status=session.session_status,
            started_at=session.started_at,
            completed_at=session.completed_at,
            question_key=answer.question_key,
            answer_family=answer.answer_family,
            has_encrypted_answer=answer.has_encrypted_answer,
            decrypted=answer.decrypted,
            answer_state=answer.answer_state,
            answer_value=answer.answer_value,
        )
        for answer in result.answers
    ]


def format_export_file(rows: list[ExportRow], *, export_format: ExportFormat, survey_id: int) -> ExportFile:
    """Serialize export rows into a CSV or JSON file body."""
    if export_format == "json":
        body = json.dumps([row.to_json_dict() for row in rows], ensure_ascii=False)
        return ExportFile(
            body=body,
            mimetype="application/json",
            filename=f"results_survey_{survey_id}.json",
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_EXPORT_FIELDNAMES)
    writer.writeheader()
    writer.writerows(row.to_json_dict() for row in rows)
    return ExportFile(
        body=output.getvalue(),
        mimetype="text/csv",
        filename=f"results_survey_{survey_id}.csv",
    )
