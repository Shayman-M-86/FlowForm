import { createFileRoute } from '@tanstack/react-router'
import { SurveyAccessTab } from '@/pages/SurveyWorkspaceTabPages/SurveyAccessTab'

export const Route = createFileRoute('/_studio/projects/$slug/surveys/$surveySlug/access')({
  component: SurveyAccessTab,
})
