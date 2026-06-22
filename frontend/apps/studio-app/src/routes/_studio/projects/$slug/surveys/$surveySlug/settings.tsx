import { createFileRoute } from '@tanstack/react-router'
import { SurveySettingsTab } from '@/pages/SurveyWorkspaceTabPages/SurveySettingsTab'

export const Route = createFileRoute('/_studio/projects/$slug/surveys/$surveySlug/settings')({
  component: SurveySettingsTab,
})
