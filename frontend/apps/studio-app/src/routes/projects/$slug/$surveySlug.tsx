import { createFileRoute, Outlet } from '@tanstack/react-router'
import { SurveyWorkspacePage } from '@/pages/SurveyWorkspacePage'

function SurveyLayout() {
  return (
    <SurveyWorkspacePage>
      <Outlet />
    </SurveyWorkspacePage>
  )
}

export const Route = createFileRoute('/projects/$slug/$surveySlug')({
  component: SurveyLayout,
})
