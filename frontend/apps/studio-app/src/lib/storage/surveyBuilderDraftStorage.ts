import type { SurveyNode } from '@flowform/builder'

const KEY_PREFIX = 'flowform.survey-builder.draft.v1'

export interface SurveyBuilderDraftRecovery {
  savedAt: number
  nodes: SurveyNode[]
}

export function surveyBuilderDraftKey(projectId: number, surveyId: number, versionId: number): string {
  return `${KEY_PREFIX}:${projectId}:${surveyId}:${versionId}`
}

export function loadSurveyBuilderDraft(projectId: number, surveyId: number, versionId: number): SurveyBuilderDraftRecovery | null {
  try {
    const raw = localStorage.getItem(surveyBuilderDraftKey(projectId, surveyId, versionId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as SurveyBuilderDraftRecovery
    if (!Array.isArray(parsed.nodes) || typeof parsed.savedAt !== 'number') return null
    return parsed
  } catch {
    return null
  }
}

export function saveSurveyBuilderDraft(projectId: number, surveyId: number, versionId: number, nodes: SurveyNode[]): void {
  try {
    const draft: SurveyBuilderDraftRecovery = { savedAt: Date.now(), nodes }
    localStorage.setItem(surveyBuilderDraftKey(projectId, surveyId, versionId), JSON.stringify(draft))
  } catch {}
}

export function clearSurveyBuilderDraft(projectId: number, surveyId: number, versionId: number): void {
  try {
    localStorage.removeItem(surveyBuilderDraftKey(projectId, surveyId, versionId))
  } catch {}
}
