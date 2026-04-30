import { useEffect, useState, type ReactNode } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { Button, Card, Spinner } from '@flowform/ui'
import { ApiRequestError } from '@/api/client'
import { useApi } from '@/api/useApi'
import { getAuthReturnTo } from '@/auth/redirect'
import { UserProvider } from '@/auth/UserContext'
import type { CurrentUserOut } from '@/api/types'

const BOOTSTRAP_SESSION_KEY = 'flowform.bootstrapped'
const USER_SESSION_KEY = 'flowform.user'
const AVATAR_SESSION_KEY = 'flowform.avatar'

function getBootstrappedUserId(): string | null {
  try {
    return window.sessionStorage.getItem(BOOTSTRAP_SESSION_KEY)
  } catch {
    return null
  }
}

function markBootstrapped(userId: string): void {
  try {
    window.sessionStorage.setItem(BOOTSTRAP_SESSION_KEY, userId)
  } catch {}
}

function clearBootstrapped(): void {
  try {
    window.sessionStorage.removeItem(BOOTSTRAP_SESSION_KEY)
    window.sessionStorage.removeItem(USER_SESSION_KEY)
    window.sessionStorage.removeItem(AVATAR_SESSION_KEY)
  } catch {}
}

function saveUserToSession(user: CurrentUserOut, avatarUrl: string | null): void {
  try {
    window.sessionStorage.setItem(USER_SESSION_KEY, JSON.stringify(user))
    if (avatarUrl) window.sessionStorage.setItem(AVATAR_SESSION_KEY, avatarUrl)
  } catch {}
}

function getUserFromSession(): CurrentUserOut | null {
  try {
    const raw = window.sessionStorage.getItem(USER_SESSION_KEY)
    return raw ? (JSON.parse(raw) as CurrentUserOut) : null
  } catch {
    return null
  }
}

function getAvatarFromSession(): string | null {
  try {
    return window.sessionStorage.getItem(AVATAR_SESSION_KEY)
  } catch {
    return null
  }
}

type Props = { children: ReactNode }

export function ProtectedApp({ children }: Props) {
  const { isLoading, isAuthenticated, getIdTokenClaims, loginWithRedirect, logout, error, user } =
    useAuth0()
  const { bootstrapCurrentUser } = useApi()

  // True immediately on refresh if a bootstrapped session exists.
  // Stays true while Auth0 does its silent check — only resets if Auth0
  // comes back saying the session is gone or a different user is now active.
  const [bootstrapReady, setBootstrapReady] = useState(() => !!getBootstrappedUserId())
  const [currentUser, setCurrentUser] = useState<CurrentUserOut | null>(getUserFromSession)
  const [avatarUrl, setAvatarUrl] = useState<string | null>(getAvatarFromSession)
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
    // Still waiting for Auth0 — don't touch bootstrapReady, let the optimistic
    // value hold so the app stays visible during the silent session check.
    if (isLoading) return

    // Auth0 finished and says the user is not authenticated.
    if (!isAuthenticated || !user?.sub) {
      clearBootstrapped()
      setBootstrapReady(false)
      setBootstrapError(null)
      setBootstrapErrorCode(null)
      return
    }

    // Auth0 confirmed a user. If it matches the session flag, we're done.
    if (getBootstrappedUserId() === user.sub) {
      setBootstrapReady(true)
      return
    }

    // Different user or no session flag — run bootstrap.
    clearBootstrapped()
    let cancelled = false
    setBootstrapReady(false)
    setBootstrapError(null)
    setBootstrapErrorCode(null)

    void (async () => {
      try {
        const claims = await getIdTokenClaims()
        const idToken = claims?.__raw
        if (!idToken) throw new Error('Auth0 did not return a raw ID token.')
        const result = await bootstrapCurrentUser(idToken)
        if (!cancelled) {
          const picture = user.picture ?? null
          markBootstrapped(user.sub!)
          saveUserToSession(result.user, picture)
          setCurrentUser(result.user)
          setAvatarUrl(picture)
          setBootstrapReady(true)
        }
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

  // Render children optimistically while Auth0 is doing its silent check,
  // as long as we have a known-good session from this browser tab.
  if (bootstrapReady && currentUser) {
    return (
      <UserProvider
        user={currentUser}
        avatarUrl={avatarUrl ?? user?.picture ?? null}
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
        <p className="auth-eyebrow">FlowForm Studio</p>
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
        <div className="flex gap-3 mt-6 flex-wrap">
          <Button variant="secondary" onClick={() => setBootstrapAttempt((n) => n + 1)}>
            Retry
          </Button>
          <Button variant="primary" onClick={() => void clearSiteDataAndLogout()}>
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
