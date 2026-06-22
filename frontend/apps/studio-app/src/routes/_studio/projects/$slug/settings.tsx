import { createFileRoute } from '@tanstack/react-router'
import { SettingsTab } from '@/pages/ProjectDashboardTabPages/SettingsTab'
import { ProjectPermissionGate } from '@/components/ProjectPermissionGate'

function SettingsTabRoute() {
  return (
    <ProjectPermissionGate anyOf={['project:edit', 'project:delete']}>
      <SettingsTab />
    </ProjectPermissionGate>
  )
}

export const Route = createFileRoute('/_studio/projects/$slug/settings')({
  component: SettingsTabRoute,
})
