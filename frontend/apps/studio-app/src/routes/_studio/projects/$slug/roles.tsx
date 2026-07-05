import { createFileRoute } from '@tanstack/react-router'
import { RolesTab } from '@/pages/ProjectDashboardTabPages/RolesTab'
import { ProjectPermissionGate } from '@/components/ProjectPermissionGate'

function RolesTabRoute() {
  return (
    <ProjectPermissionGate anyOf={['project:manage_roles']}>
      <RolesTab />
    </ProjectPermissionGate>
  )
}

export const Route = createFileRoute('/_studio/projects/$slug/roles')({
  component: RolesTabRoute,
})
