import { createFileRoute } from '@tanstack/react-router'
import { RespondPage } from '@/pages/RespondPage'

export const Route = createFileRoute('/_respondent/s/$slug')({
  component: PublicSurveyRouteComponent,
})

function PublicSurveyRouteComponent() {
  const { slug } = Route.useParams()
  return <RespondPage publicSlug={slug} />
}
