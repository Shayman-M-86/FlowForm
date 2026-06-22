import { createFileRoute } from '@tanstack/react-router'
import { SurveyOverviewTab } from '@/pages/SurveyWorkspaceTabPages/SurveyOverviewTab'

export const Route = createFileRoute('/_studio/projects/$slug/surveys/$surveySlug/overview')({
  component: SurveyOverviewTab,
})
