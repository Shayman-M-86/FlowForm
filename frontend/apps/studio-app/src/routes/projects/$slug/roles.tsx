import { createFileRoute } from '@tanstack/react-router'
import { RolesTab } from '@/pages/ProjectDashboardTabPages/RolesTab'

export const Route = createFileRoute('/projects/$slug/roles')({
  component: RolesTab,
})
