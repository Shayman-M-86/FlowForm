import type { ReactNode } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { Button, Card, Spinner } from '@flowform/ui'
import { getAuthReturnTo } from '@/auth/redirect'
import { useBootstrap } from '@/auth/bootstrap/useBootstrap'
import { UserProvider } from '@/auth/UserContext'
import { useRenderDebug } from '@/debug/useRenderDebug'

type Props = { children: ReactNode }

export function ProtectedApp({ children }: Props) {
  useRenderDebug('ProtectedApp', { children })
  return <AuthenticatedProtectedApp>{children}</AuthenticatedProtectedApp>
}

function AuthenticatedProtectedApp({ children }: Props) {
  useRenderDebug('AuthenticatedProtectedApp', { children })
  const { isLoading, isAuthenticated, loginWithRedirect, error, user } = useAuth0()
  const { bootstrapReady, currentUser, avatarUrl, error: bootstrapError, errorCode, retry, updateUser, clearAndLogout } = useBootstrap()

  if (bootstrapReady && currentUser) {
    return (
      <UserProvider
        user={currentUser}
        avatarUrl={avatarUrl ?? user?.picture ?? null}
        updateUser={updateUser}
      >
        {children}
      </UserProvider>
    )
  }

  if (bootstrapReady) return <>{children}</>

  if (isLoading) {
    return (
      <AuthGate>
        <p className="auth-eyebrow">FlowForm Studio</p>
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
          <Button variant="primary" onClick={() => loginWithRedirect({ appState: { returnTo: getAuthReturnTo() } })}>
            Try again
          </Button>
          <Button variant="secondary" onClick={() => void clearAndLogout()}>
            Log out
          </Button>
        </div>
      </AuthGate>
    )
  }

  if (!isAuthenticated) {
    return (
      <AuthGate>
        <p className="auth-eyebrow">FlowForm Studio</p>
        <h1 className="text-2xl font-semibold mt-1 mb-3">Sign in to continue</h1>
        <p className="text-muted-foreground text-sm leading-relaxed">
          You need to log in to access your projects, surveys, and submissions.
        </p>
        <div className="flex gap-3 mt-6 flex-wrap">
          <Button variant="primary" onClick={() => loginWithRedirect({ appState: { returnTo: getAuthReturnTo() } })}>
            Log in
          </Button>
          <Button
            variant="secondary"
            onClick={() => loginWithRedirect({ appState: { returnTo: getAuthReturnTo() }, authorizationParams: { screen_hint: 'signup' } })}
          >
            Create account
          </Button>
        </div>
      </AuthGate>
    )
  }

  const needsLogin = errorCode === 'AUTH0_CLIENT_ID_NOT_CONFIGURED'

  return (
    <AuthGate>
      <h1 className="text-2xl font-semibold mb-3">
        {needsLogin ? 'Sign in to continue' : bootstrapError ? 'Account setup failed' : 'Setting up your account'}
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
          <Button variant="primary" onClick={() => loginWithRedirect({ appState: { returnTo: getAuthReturnTo() } })}>
            Log in
          </Button>
          <Button variant="secondary" onClick={() => void clearAndLogout()}>
            Log out
          </Button>
        </div>
      )}
      {bootstrapError && !needsLogin && (
        <div className="flex gap-3 mt-6 flex-wrap">
          <Button variant="secondary" onClick={retry}>
            Retry
          </Button>
          <Button variant="primary" onClick={() => void clearAndLogout()}>
            Log out and retry
          </Button>
        </div>
      )}
    </AuthGate>
  )
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
