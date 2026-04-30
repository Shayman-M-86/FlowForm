import { createFileRoute } from '@tanstack/react-router'
import { ProjectDashboardPage } from '@/pages/ProjectDashboardPage'

export const Route = createFileRoute('/projects/$slug/')({
  component: ProjectDashboardPage,
})
