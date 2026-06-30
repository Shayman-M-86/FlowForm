import { createFileRoute } from '@tanstack/react-router'
import { InvitationPage } from '@/pages/InvitationPage'

export const Route = createFileRoute('/_public/invitations/$token')({
  component: InvitationRouteComponent,
})

function InvitationRouteComponent() {
  const { token } = Route.useParams()
  return <InvitationPage token={token} />
}
