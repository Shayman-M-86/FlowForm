import { createFileRoute } from '@tanstack/react-router'
import { SurveyBuilderTab } from '@/pages/SurveyWorkspaceTabPages/SurveyBuilderTab'

export const Route = createFileRoute('/projects/$slug/$surveySlug/builder')({
  component: SurveyBuilderTab,
})
