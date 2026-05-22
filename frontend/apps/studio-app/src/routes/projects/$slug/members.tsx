import { createFileRoute } from '@tanstack/react-router'
import { MembersTab } from '@/pages/ProjectDashboardTabPages/MembersTab'
import { useProject } from '@/api/projects/hooks'

function MembersTabRoute() {
  const { slug } = Route.useParams()
  const { data: project } = useProject(slug)
  if (!project) return null
  return <MembersTab projectId={project.id} />
}

export const Route = createFileRoute('/projects/$slug/members')({
  component: MembersTabRoute,
})
