import { createFileRoute } from '@tanstack/react-router'
import { SurveySettingsTab } from '@/pages/SurveyWorkspaceTabPages/SurveySettingsTab'

export const Route = createFileRoute('/projects/$slug/$surveySlug/settings')({
  component: SurveySettingsTab,
})
