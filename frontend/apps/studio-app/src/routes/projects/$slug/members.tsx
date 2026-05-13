import { createFileRoute } from '@tanstack/react-router'
import { MembersTab } from '@/pages/ProjectDashboardTabPages/MembersTab'

export const Route = createFileRoute('/projects/$slug/members')({
  component: MembersTab,
})
