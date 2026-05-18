import { createFileRoute } from '@tanstack/react-router'
import { SurveysTab } from '@/pages/ProjectDashboardTabPages/SurveysTab'
import { useRenderDebug } from '@/debug/useRenderDebug'

function SurveysTabWrapper() {
  useRenderDebug('SurveysTabWrapper')
  const { slug } = Route.useParams()
  return <SurveysTab projectSlug={slug} />
}

export const Route = createFileRoute('/projects/$slug/surveys/')({
  component: SurveysTabWrapper,
})
