import { createFileRoute } from '@tanstack/react-router'
import { SurveysTab } from '@/pages/ProjectDashboardTabPages/SurveysTab'
import { ProjectPermissionGate } from '@/components/ProjectPermissionGate'
import { useRenderDebug } from '@/debug/useRenderDebug'

function SurveysTabWrapper() {
  useRenderDebug('SurveysTabWrapper')
  const { slug } = Route.useParams()
  return (
    <ProjectPermissionGate anyOf={['survey:view']}>
      <SurveysTab projectSlug={slug} />
    </ProjectPermissionGate>
  )
}

export const Route = createFileRoute('/projects/$slug/surveys/')({
  component: SurveysTabWrapper,
})
