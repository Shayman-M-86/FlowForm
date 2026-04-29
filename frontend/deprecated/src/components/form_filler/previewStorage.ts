import type { SurveyNode } from "../node/questionTypes";

export const FORM_FILLER_PREVIEW_STORAGE_KEY = "flowform.form-filler.preview";

export function savePreviewSurvey(survey: SurveyNode[]) {
  if (typeof window === "undefined") return;

  try {
    window.sessionStorage.setItem(FORM_FILLER_PREVIEW_STORAGE_KEY, JSON.stringify(survey));
  } catch {
    // Ignore storage failures in preview mode.
  }
}

export function loadPreviewSurvey(): SurveyNode[] {
  if (typeof window === "undefined") return [];

  try {
    const stored = window.sessionStorage.getItem(FORM_FILLER_PREVIEW_STORAGE_KEY);
    if (!stored) return [];

    const parsed: unknown = JSON.parse(stored);
    return isSurveyNodeArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function isSurveyNodeArray(value: unknown): value is SurveyNode[] {
  return Array.isArray(value) && value.every((entry) => {
    if (!entry || typeof entry !== "object") return false;

    const node = entry as Partial<SurveyNode> & { content?: unknown };
    return (
      (node.type === "question" || node.type === "rule") &&
      typeof node.sort_key === "number" &&
      !!node.content &&
      typeof node.content === "object"
    );
  });
}
