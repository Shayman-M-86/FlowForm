import { createFileRoute } from '@tanstack/react-router'
import { SubjectsTab } from '@/pages/ProjectDashboardTabPages/SubjectsTab'
import { useProject } from '@/api/hooks/projects'
import { ProjectPermissionGate } from '@/components/ProjectPermissionGate'

function SubjectsTabRoute() {
  const { slug } = Route.useParams()
  const { data: project } = useProject(slug)
  return (
    <ProjectPermissionGate anyOf={['project:manage_members']}>
      {project ? <SubjectsTab projectId={project.id} /> : null}
    </ProjectPermissionGate>
  )
}

export const Route = createFileRoute('/_studio/projects/$slug/subjects')({
  component: SubjectsTabRoute,
})
