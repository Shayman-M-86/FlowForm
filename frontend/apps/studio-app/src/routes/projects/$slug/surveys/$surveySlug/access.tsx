import { createFileRoute } from '@tanstack/react-router'
import { SurveyAccessTab } from '@/pages/SurveyWorkspaceTabPages/SurveyAccessTab'

export const Route = createFileRoute('/projects/$slug/surveys/$surveySlug/access')({
  component: SurveyAccessTab,
})
