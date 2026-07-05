import { createFileRoute } from '@tanstack/react-router'
import { RespondPage } from '@/pages/RespondPage'

export const Route = createFileRoute('/_respondent/respond/$token')({
  component: RespondRouteComponent,
})

function RespondRouteComponent() {
  const { token } = Route.useParams()
  return <RespondPage token={token} />
}
