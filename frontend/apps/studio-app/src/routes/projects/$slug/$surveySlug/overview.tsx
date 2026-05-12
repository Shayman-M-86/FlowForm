import { createFileRoute } from '@tanstack/react-router'
import { SurveyOverviewTab } from '@/pages/SurveyWorkspaceTabPages/SurveyOverviewTab'

export const Route = createFileRoute('/projects/$slug/$surveySlug/overview')({
  component: SurveyOverviewTab,
})
