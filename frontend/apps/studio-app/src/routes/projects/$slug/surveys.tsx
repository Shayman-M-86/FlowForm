import { createFileRoute } from '@tanstack/react-router'
import { ProjectSurveysPage } from '@/pages/ProjectSurveysPage'

export const Route = createFileRoute('/projects/$slug/surveys')({
  component: ProjectSurveysPage,
})
