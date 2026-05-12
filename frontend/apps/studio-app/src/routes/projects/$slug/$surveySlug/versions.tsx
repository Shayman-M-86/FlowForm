import { createFileRoute } from '@tanstack/react-router'
import { SurveyVersionsTab } from '@/pages/SurveyWorkspaceTabPages/SurveyVersionsTab'

export const Route = createFileRoute('/projects/$slug/$surveySlug/versions')({
  component: SurveyVersionsTab,
})
