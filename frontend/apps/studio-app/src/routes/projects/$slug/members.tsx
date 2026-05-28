import { createFileRoute } from '@tanstack/react-router'
import { MembersTab } from '@/pages/ProjectDashboardTabPages/MembersTab'
import { useProject } from '@/api/project/projects/hooks'
import { ProjectPermissionGate } from '@/components/ProjectPermissionGate'

function MembersTabRoute() {
  const { slug } = Route.useParams()
  const { data: project } = useProject(slug)
  return (
    <ProjectPermissionGate anyOf={['project:manage_members']}>
      {project ? <MembersTab projectId={project.id} /> : null}
    </ProjectPermissionGate>
  )
}

export const Route = createFileRoute('/projects/$slug/members')({
  component: MembersTabRoute,
})
