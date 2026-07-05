import { createFileRoute } from '@tanstack/react-router'
import { SurveyResponsesTab } from '@/pages/SurveyWorkspaceTabPages/SurveyResponsesTab'

export const Route = createFileRoute('/_studio/projects/$slug/surveys/$surveySlug/responses')({
  component: SurveyResponsesTab,
})
