import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { FormFiller } from "../components/form_filler/FormFiller";
import {
  isSurveyNodeArray,
  loadPreviewSurvey,
  savePreviewSurvey,
} from "../components/form_filler/previewStorage";
import type { SurveyNode } from "../components/node/questionTypes";

interface PreviewRouteState {
  survey?: SurveyNode[];
}

export function FormFillerPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [survey, setSurvey] = useState<SurveyNode[]>(() => readSurveyFromState(location.state) ?? loadPreviewSurvey());

  useEffect(() => {
    const nextSurvey = readSurveyFromState(location.state);
    if (nextSurvey) {
      setSurvey(nextSurvey);
    }
  }, [location.state]);

  useEffect(() => {
    if (survey.length > 0) {
      savePreviewSurvey(survey);
    }
  }, [survey]);

  return (
    <FormFiller
      survey={survey}
      title="Form Filler"
      description="Complete each survey step to move through the current flow."
      emptyTitle="No survey JSON is loaded"
      emptyMessage="Open the node builder and use the preview button after creating at least one question."
      exitLabel="Back to builder"
      onExit={() => navigate("/node")}
      showAnswerSummary
      stackSidebar
    />
  );
}

function readSurveyFromState(state: unknown): SurveyNode[] | null {
  if (!state || typeof state !== "object") return null;

  const survey = (state as PreviewRouteState).survey;
  return isSurveyNodeArray(survey) ? survey : null;
}
