import { createFileRoute } from '@tanstack/react-router'
import { SurveyMembersTab } from '@/pages/SurveyWorkspaceTabPages/SurveyMembersTab'

export const Route = createFileRoute('/projects/$slug/$surveySlug/members')({
  component: SurveyMembersTab,
})
