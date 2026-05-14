import { createFileRoute } from '@tanstack/react-router'
import { SurveyRolesTab } from '@/pages/SurveyWorkspaceTabPages/SurveyRolesTab'

export const Route = createFileRoute('/projects/$slug/surveys/$surveySlug/roles')({
  component: SurveyRolesTab,
})
