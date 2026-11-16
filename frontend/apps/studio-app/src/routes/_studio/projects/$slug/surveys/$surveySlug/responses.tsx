import { createFileRoute } from '@tanstack/react-router'
import type { ResponseStatus } from '@/api/hooks/results'
import { SurveyResponsesTab } from '@/pages/SurveyWorkspaceTabPages/SurveyResponsesTab'

const RESPONSE_STATUSES: readonly ResponseStatus[] = ['completed', 'in_progress', 'abandoned']

type SurveyResponsesSearch = {
  status?: ResponseStatus
}

export const Route = createFileRoute('/_studio/projects/$slug/surveys/$surveySlug/responses')({
  validateSearch: (search: Record<string, unknown>): SurveyResponsesSearch => {
    const status = search.status
    return RESPONSE_STATUSES.includes(status as ResponseStatus) ? { status: status as ResponseStatus } : {}
  },
  component: SurveyResponsesTab,
})
