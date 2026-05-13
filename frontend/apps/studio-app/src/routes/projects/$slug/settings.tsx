import { createFileRoute } from '@tanstack/react-router'
import { SettingsTab } from '@/pages/ProjectDashboardTabPages/SettingsTab'

export const Route = createFileRoute('/projects/$slug/settings')({
  component: SettingsTab,
})
