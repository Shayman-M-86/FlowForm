import { useCallback, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useAuth0 } from '@auth0/auth0-react'
import { Button, Card, Spinner } from '@flowform/ui'
import { useProjects } from '@/api/hooks/projects'
import {
  useAcceptInvitationByToken,
  useDeclineInvitation,
  useMyInvitations,
  useResolveInvitationByToken,
} from '@/api/hooks/members'
import type { components } from '@/api/generated/schema'

type ResolveResponse = components['schemas']['PublicInvitationResolveResponse']

type PageState =
  | { phase: 'loading' }
  | { phase: 'resolved'; invitation: ResolveResponse }
  | { phase: 'email-mismatch'; invitation: ResolveResponse; userEmail: string }
  | { phase: 'accepting'; invitation: ResolveResponse }
  | { phase: 'accepted'; projectName: string; projectSlug: string }
  | { phase: 'already-handled'; status: string; projectName: string }
  | { phase: 'error'; message: string }

// Terminal outcome of a mutation the user just triggered on this page.
// Once set it overrides the phase derived from query state, since the
// underlying resolve query may not have refetched yet (or its data no
// longer reflects what the user just did).
type MutationOutcome =
  | { kind: 'accepted'; projectName: string; projectSlug: string }
  | { kind: 'declined'; projectName: string }

interface InvitationPageProps {
  token: string
}

export function InvitationPage({ token }: InvitationPageProps) {
  const { isLoading: isAuthLoading, isAuthenticated, user, loginWithRedirect, logout } = useAuth0()
  const navigate = useNavigate()
  const resolved = useResolveInvitationByToken(token)
  const projects = useProjects(isAuthenticated)
  const myInvitations = useMyInvitations(isAuthenticated)
  const accept = useAcceptInvitationByToken()
  const decline = useDeclineInvitation()
  const [declining, setDeclining] = useState(false)
  const [outcome, setOutcome] = useState<MutationOutcome | null>(null)

  const state: PageState = (() => {
    if (outcome?.kind === 'accepted') {
      return { phase: 'accepted', projectName: outcome.projectName, projectSlug: outcome.projectSlug }
    }
    if (outcome?.kind === 'declined') {
      return { phase: 'already-handled', status: 'declined', projectName: outcome.projectName }
    }
    if (isAuthLoading || resolved.isLoading) return { phase: 'loading' }
    if (resolved.isError || !resolved.data) {
      return { phase: 'error', message: 'This invitation link is invalid or has expired.' }
    }

    const data = resolved.data
    if (data.status !== 'pending') {
      return { phase: 'already-handled', status: data.status, projectName: data.project_name }
    }
    if (!isAuthenticated || !user?.email) {
      return { phase: 'resolved', invitation: data }
    }
    if (user.email.toLowerCase() !== data.invited_email.toLowerCase()) {
      return { phase: 'email-mismatch', invitation: data, userEmail: user.email }
    }
    return { phase: 'accepting', invitation: data }
  })()

  const handleAccept = useCallback((acceptToken: string, projectName: string) => {
    accept.mutate(acceptToken, {
      onSuccess: (member) => {
        const project = projects.data?.find((p) => p.id === member.project_id)
        setOutcome({ kind: 'accepted', projectName, projectSlug: project?.slug ?? '' })
      },
    })
  }, [accept, projects.data])

  const handleDecline = useCallback(async (invitedEmail: string) => {
    setDeclining(true)
    try {
      const { data: invitations } = await myInvitations.refetch()
      const match = invitations?.find(
        (inv) => inv.invited_email.toLowerCase() === invitedEmail.toLowerCase()
          && inv.status === 'pending',
      )
      if (!match) {
        setDeclining(false)
        return
      }
      decline.mutate(match.id, {
        onSuccess: () => {
          setOutcome({ kind: 'declined', projectName: resolved.data?.project_name ?? 'the project' })
        },
        onSettled: () => setDeclining(false),
      })
    } catch {
      setDeclining(false)
    }
  }, [decline, myInvitations, resolved.data?.project_name])

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
              onClick={() => void handleDecline(state.invitation.invited_email)}
              disabled={declining || accept.isPending}
            >
              {declining ? 'Declining…' : 'Decline'}
            </Button>
            <Button
              variant="primary"
              onClick={() => handleAccept(token, state.invitation.project_name)}
              disabled={accept.isPending || declining}
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
