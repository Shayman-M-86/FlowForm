import { createFileRoute } from '@tanstack/react-router'
import { SurveyLinksTab } from '@/pages/SurveyWorkspaceTabPages/SurveyLinksTab'

export const Route = createFileRoute('/projects/$slug/surveys/$surveySlug/links')({
  component: SurveyLinksTab,
})
