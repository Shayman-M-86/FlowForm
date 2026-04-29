import { useEffect, useState, type ReactNode } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { Button, Card, Spinner } from '@flowform/ui'
import { ApiRequestError } from '@/api/client'
import { useApi } from '@/api/useApi'
import { getAuthReturnTo } from '@/auth/redirect'

type Props = { children: ReactNode }

export function ProtectedApp({ children }: Props) {
  const { isLoading, isAuthenticated, getIdTokenClaims, loginWithRedirect, logout, error, user } =
    useAuth0()
  const { bootstrapCurrentUser } = useApi()

  const [bootstrapReady, setBootstrapReady] = useState(false)
  const [bootstrapError, setBootstrapError] = useState<string | null>(null)
  const [bootstrapErrorCode, setBootstrapErrorCode] = useState<string | null>(null)
  const [bootstrapAttempt, setBootstrapAttempt] = useState(0)

  async function clearSiteDataAndLogout() {
    try {
      window.localStorage.clear()
      window.sessionStorage.clear()
      if ('caches' in window) {
        const keys = await window.caches.keys()
        await Promise.all(keys.map((k) => window.caches.delete(k)))
      }
    } finally {
      await logout({ logoutParams: { returnTo: window.location.origin } })
    }
  }

  useEffect(() => {
    if (isLoading || !isAuthenticated || !user?.sub) {
      setBootstrapReady(false)
      setBootstrapError(null)
      setBootstrapErrorCode(null)
      return
    }

    let cancelled = false
    setBootstrapReady(false)
    setBootstrapError(null)
    setBootstrapErrorCode(null)

    void (async () => {
      try {
        const claims = await getIdTokenClaims()
        const idToken = claims?.__raw
        if (!idToken) throw new Error('Auth0 did not return a raw ID token.')
        await bootstrapCurrentUser(idToken)
        if (!cancelled) setBootstrapReady(true)
      } catch (err) {
        if (!cancelled) {
          setBootstrapReady(false)
          setBootstrapErrorCode(err instanceof ApiRequestError ? err.error.code : null)
          setBootstrapError(
            err instanceof Error ? err.message : 'Failed to finish account setup.',
          )
        }
      }
    })()

    return () => { cancelled = true }
  }, [bootstrapAttempt, bootstrapCurrentUser, getIdTokenClaims, isAuthenticated, isLoading, user?.sub])

  if (isLoading) {
    return (
      <AuthGate>
        <p className="auth-eyebrow">FlowForm Admin</p>
        <h1 className="text-2xl font-semibold mt-1 mb-3">Checking session</h1>
        <div className="flex items-center gap-3 text-muted-foreground">
          <Spinner size={18} />
          <span className="text-sm">Loading your workspace…</span>
        </div>
      </AuthGate>
    )
  }

  if (error) {
    return (
      <AuthGate>
        <h1 className="text-2xl font-semibold mb-3">Authentication error</h1>
        <p className="text-muted-foreground text-sm">{error.message}</p>
        <div className="flex gap-3 mt-6 flex-wrap">
          <Button
            variant="primary"
            onClick={() => loginWithRedirect({ appState: { returnTo: getAuthReturnTo() } })}
          >
            Try again
          </Button>
          <Button variant="secondary" onClick={() => void clearSiteDataAndLogout()}>
            Log out
          </Button>
        </div>
      </AuthGate>
    )
  }

  if (!isAuthenticated) {
    return (
      <AuthGate>
        <p className="auth-eyebrow">FlowForm Admin</p>
        <h1 className="text-2xl font-semibold mt-1 mb-3">Sign in to continue</h1>
        <p className="text-muted-foreground text-sm leading-relaxed">
          You need to log in to access your projects, surveys, and submissions.
        </p>
        <div className="flex gap-3 mt-6 flex-wrap">
          <Button
            variant="primary"
            onClick={() => loginWithRedirect({ appState: { returnTo: getAuthReturnTo() } })}
          >
            Log in
          </Button>
          <Button
            variant="secondary"
            onClick={() =>
              loginWithRedirect({
                appState: { returnTo: getAuthReturnTo() },
                authorizationParams: { screen_hint: 'signup' },
              })
            }
          >
            Create account
          </Button>
        </div>
      </AuthGate>
    )
  }

  const needsLogin = bootstrapErrorCode === 'AUTH0_CLIENT_ID_NOT_CONFIGURED'

  if (!bootstrapReady) {
    return (
      <AuthGate>
        <h1 className="text-2xl font-semibold mb-3">
          {needsLogin
            ? 'Sign in to continue'
            : bootstrapError
              ? 'Account setup failed'
              : 'Setting up your account'}
        </h1>
        <p className="text-muted-foreground text-sm leading-relaxed">
          {needsLogin
            ? 'FlowForm could not finish account setup because Auth0 is not fully configured on the backend. Sign in again after the configuration is restored.'
            : bootstrapError ?? 'Finishing your FlowForm account before opening the workspace.'}
        </p>
        {!bootstrapError && !needsLogin && (
          <div className="flex items-center gap-3 mt-6 text-muted-foreground">
            <Spinner size={18} />
            <span className="text-sm">One moment…</span>
          </div>
        )}
        {needsLogin && (
          <div className="flex gap-3 mt-6 flex-wrap">
            <Button
              variant="primary"
              onClick={() => loginWithRedirect({ appState: { returnTo: getAuthReturnTo() } })}
            >
              Log in
            </Button>
            <Button variant="secondary" onClick={() => void clearSiteDataAndLogout()}>
              Log out
            </Button>
          </div>
        )}
        {bootstrapError && !needsLogin && (
          <div className="mt-6">
            <Button variant="secondary" onClick={() => setBootstrapAttempt((n) => n + 1)}>
              Retry
            </Button>
          </div>
        )}
      </AuthGate>
    )
  }

  return <>{children}</>
}

function AuthGate({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen grid place-items-center p-6 bg-background">
      <Card size="lg" className="w-full max-w-lg">
        {children}
      </Card>
    </div>
  )
}
