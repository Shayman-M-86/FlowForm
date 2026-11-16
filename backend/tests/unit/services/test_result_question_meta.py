from uuid import uuid4

from app.schema.orm.core.survey_content import SurveyQuestion
from app.services.admin_results.core.question_meta import build_question_meta_map


def test_question_metadata_keeps_historical_wording_and_options() -> None:
    node_id = uuid4()
    question = SurveyQuestion(
        id=node_id,
        survey_version_id=7,
        question_key="coffee_time",
        sort_key=200,
        node_type="question",
        question_schema={
            "family": "choice",
            "label": "When do you drink coffee?",
            "definition": {"min": 0, "max": 1, "options": [{"id": "morning", "label": "In the morning"}]},
        },
    )

    metadata = build_question_meta_map([question])[node_id]
    assert metadata.key == "coffee_time"
    assert metadata.family == "choice"
    assert metadata.sort_key == 200
    assert metadata.content is not None
    assert metadata.content["label"] == "When do you drink coffee?"
    assert metadata.content["definition"]["options"][0]["label"] == "In the morning"
