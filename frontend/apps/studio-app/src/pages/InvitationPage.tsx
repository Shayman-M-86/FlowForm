import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useAuth0 } from '@auth0/auth0-react'
import { Button, Card, Spinner } from '@flowform/ui'
import { apiClient } from '@/api/client'
import { useAcceptInvitation, useDeclineInvitation } from '@/api/hooks/members'
import type { components } from '@/api/generated/schema'

type ResolveResponse = components['schemas']['PublicInvitationResolveResponse']

type PageState =
  | { phase: 'loading' }
  | { phase: 'resolved'; invitation: ResolveResponse }
  | { phase: 'email-mismatch'; invitation: ResolveResponse; userEmail: string }
  | { phase: 'accepting'; invitation: ResolveResponse; invitationId: number }
  | { phase: 'accepted'; projectName: string; projectSlug: string }
  | { phase: 'already-handled'; status: string; projectName: string }
  | { phase: 'error'; message: string }

interface InvitationPageProps {
  token: string
}

export function InvitationPage({ token }: InvitationPageProps) {
  const [state, setState] = useState<PageState>({ phase: 'loading' })
  const { isLoading: isAuthLoading, isAuthenticated, user, loginWithRedirect, logout } = useAuth0()
  const navigate = useNavigate()
  const accept = useAcceptInvitation()
  const decline = useDeclineInvitation()
  const resolvedRef = useRef<ResolveResponse | null>(null)

  useEffect(() => {
    if (isAuthLoading) return

    let cancelled = false

    async function resolve() {
      const { data, error } = await apiClient.GET(
        '/api/v1/account/invitations/resolve/{token}',
        { params: { path: { token } } },
      )

      if (cancelled) return

      if (error || !data) {
        setState({ phase: 'error', message: 'This invitation link is invalid or has expired.' })
        return
      }

      resolvedRef.current = data

      if (data.status !== 'pending') {
        const labels: Record<string, string> = {
          accepted: 'This invitation has already been accepted.',
          declined: 'This invitation has been declined.',
          revoked: 'This invitation has been revoked.',
        }
        setState({
          phase: 'already-handled',
          status: data.status,
          projectName: data.project_name,
        })
        return
      }

      if (!isAuthenticated || !user?.email) {
        setState({ phase: 'resolved', invitation: data })
        return
      }

      if (user.email.toLowerCase() !== data.invited_email.toLowerCase()) {
        setState({ phase: 'email-mismatch', invitation: data, userEmail: user.email })
        return
      }

      const { data: myInvitations, error: listError } = await apiClient.GET(
        '/api/v1/account/invitations',
      )

      if (cancelled) return

      if (listError || !myInvitations) {
        setState({ phase: 'error', message: 'Failed to load your invitations.' })
        return
      }

      const match = myInvitations.find(
        (inv) => inv.invited_email.toLowerCase() === data.invited_email.toLowerCase()
          && inv.status === 'pending',
      )

      if (!match) {
        setState({ phase: 'error', message: 'Could not find a matching pending invitation for your account.' })
        return
      }

      setState({ phase: 'accepting', invitation: data, invitationId: match.id })
    }

    void resolve()
    return () => { cancelled = true }
  }, [token, isAuthLoading, isAuthenticated, user?.email])

  const handleAccept = useCallback((invitationId: number, projectName: string) => {
    accept.mutate(invitationId, {
      onSuccess: async (member) => {
        const { data: project } = await apiClient.GET(
          '/api/v1/studio/projects/{project_id}',
          { params: { path: { project_id: member.project_id } } },
        )
        setState({
          phase: 'accepted',
          projectName,
          projectSlug: project?.slug ?? '',
        })
      },
    })
  }, [accept])

  const handleDecline = useCallback((invitationId: number) => {
    decline.mutate(invitationId, {
      onSuccess: () => {
        setState({ phase: 'already-handled', status: 'declined', projectName: resolvedRef.current?.project_name ?? 'the project' })
      },
    })
  }, [decline])

  const handleSignIn = useCallback((invitation: ResolveResponse) => {
    void loginWithRedirect({
      appState: { returnTo: window.location.pathname },
      authorizationParams: { login_hint: invitation.invited_email },
    })
  }, [loginWithRedirect])

  const handleSignUp = useCallback((invitation: ResolveResponse) => {
    void loginWithRedirect({
      appState: { returnTo: window.location.pathname },
      authorizationParams: { login_hint: invitation.invited_email, screen_hint: 'signup' as const },
    })
  }, [loginWithRedirect])

  const handleSwitchAccount = useCallback(() => {
    const invitationPath = window.location.pathname
    window.localStorage.clear()
    window.sessionStorage.clear()
    sessionStorage.setItem('ff:invitation-return', invitationPath)
    void logout({ logoutParams: { returnTo: window.location.origin } })
  }, [logout])

  switch (state.phase) {
    case 'loading':
      return (
        <CenteredCard>
          <div className="flex items-center gap-3 text-muted-foreground">
            <Spinner size={18} />
            <span className="text-sm">Loading invitation…</span>
          </div>
        </CenteredCard>
      )

    case 'resolved':
      return (
        <CenteredCard>
          <h1 className="text-2xl font-semibold mb-3">You&rsquo;re invited</h1>
          <div className="grid gap-1 mb-6">
            <p className="text-sm text-foreground">
              <span className="font-semibold">{state.invitation.inviter_name ?? 'A team member'}</span>
              {' '}has invited you to join{' '}
              <span className="font-semibold">{state.invitation.project_name}</span>.
            </p>
            <p className="text-xs text-muted-foreground">
              Invitation sent to {state.invitation.invited_email}
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <Button variant="primary" onClick={() => handleSignIn(state.invitation)}>
              Sign in
            </Button>
            <Button variant="secondary" onClick={() => handleSignUp(state.invitation)}>
              Create account
            </Button>
          </div>
        </CenteredCard>
      )

    case 'email-mismatch':
      return (
        <CenteredCard>
          <h1 className="text-2xl font-semibold mb-3">Wrong account</h1>
          <p className="text-muted-foreground text-sm mb-6">
            This invitation was sent to <span className="font-semibold">{state.invitation.invited_email}</span>,
            but you&rsquo;re signed in as <span className="font-semibold">{state.userEmail}</span>.
            Please sign in with the correct account.
          </p>
          <Button variant="primary" onClick={handleSwitchAccount}>
            Sign in with a different account
          </Button>
        </CenteredCard>
      )

    case 'accepting':
      return (
        <CenteredCard>
          <h1 className="text-2xl font-semibold mb-3">Welcome to FlowForm</h1>
          <div className="grid gap-1 mb-6">
            <p className="text-sm text-foreground">
              <span className="font-semibold">{state.invitation.inviter_name ?? 'A team member'}</span>
              {' '}has invited you to join{' '}
              <span className="font-semibold">{state.invitation.project_name}</span>.
            </p>
          </div>
          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => handleDecline(state.invitationId)}
              disabled={decline.isPending || accept.isPending}
            >
              {decline.isPending ? 'Declining…' : 'Decline'}
            </Button>
            <Button
              variant="primary"
              onClick={() => handleAccept(state.invitationId, state.invitation.project_name)}
              disabled={accept.isPending || decline.isPending}
            >
              {accept.isPending ? 'Accepting…' : 'Accept invitation'}
            </Button>
          </div>
        </CenteredCard>
      )

    case 'accepted':
      return (
        <CenteredCard>
          <h1 className="text-2xl font-semibold mb-3">You&rsquo;re in!</h1>
          <p className="text-muted-foreground text-sm mb-6">
            You&rsquo;ve joined <span className="font-semibold">{state.projectName}</span>.
          </p>
          <Button
            variant="primary"
            onClick={() => void navigate({
              to: state.projectSlug ? '/projects/$slug' : '/',
              params: state.projectSlug ? { slug: state.projectSlug } : undefined,
            })}
          >
            Go to project
          </Button>
        </CenteredCard>
      )

    case 'already-handled':
      return (
        <CenteredCard>
          <h1 className="text-2xl font-semibold mb-3">Invitation {state.status}</h1>
          <p className="text-muted-foreground text-sm mb-6">
            {state.status === 'accepted'
              ? `You've already joined ${state.projectName}.`
              : state.status === 'declined'
                ? 'This invitation has been declined.'
                : 'This invitation is no longer available.'}
          </p>
          {state.status === 'accepted' && (
            <Button variant="primary" onClick={() => void navigate({ to: '/' })}>
              Go to dashboard
            </Button>
          )}
        </CenteredCard>
      )

    case 'error':
      return (
        <CenteredCard>
          <h1 className="text-2xl font-semibold mb-3">Unable to load invitation</h1>
          <p className="text-muted-foreground text-sm">{state.message}</p>
        </CenteredCard>
      )
  }
}

function CenteredCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen grid place-items-center p-6 bg-background">
      <Card size="xl" className="w-full max-w-lg">
        {children}
      </Card>
    </div>
  )
}
