// frontend/apps/studio-app/src/auth/bootstrap/useBootstrap.ts
import { useEffect, useState } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { initApiAuth } from '@/api/client'
import { bootstrapCurrentUser } from './api'
import type { CurrentUserResponses } from '@/api/generated/schema'
import {
  getBootstrappedUserId,
  markBootstrapped,
  clearBootstrapped,
  saveUserToSession,
  getUserFromSession,
  getAvatarFromSession,
} from './session'

export interface BootstrapState {
  bootstrapReady: boolean
  currentUser: CurrentUserResponses | null
  avatarUrl: string | null
  error: string | null
  errorCode: string | null
  retry: () => void
  updateUser: (user: CurrentUserResponses) => void
  clearAndLogout: () => Promise<void>
}

function hasMessage(err: unknown): err is { message: string } {
  return typeof err === 'object' && err !== null && 'message' in err && typeof (err as Record<string, unknown>).message === 'string'
}

function hasCode(err: unknown): err is { code: string } {
  return typeof err === 'object' && err !== null && 'code' in err && typeof (err as Record<string, unknown>).code === 'string'
}

export function useBootstrap(): BootstrapState {
  const {
    isLoading,
    isAuthenticated,
    getIdTokenClaims,
    getAccessTokenSilently,
    logout,
    user,
  } = useAuth0()

  useEffect(() => {
    initApiAuth(() =>
      getAccessTokenSilently({
        authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE as string },
      }),
    )
  }, [getAccessTokenSilently])

  const [bootstrapReady, setBootstrapReady] = useState(() => !!getBootstrappedUserId())
  const [currentUser, setCurrentUser] = useState<CurrentUserResponses | null>(getUserFromSession)
  const [avatarUrl, setAvatarUrl] = useState<string | null>(getAvatarFromSession)
  const [error, setError] = useState<string | null>(null)
  const [errorCode, setErrorCode] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  async function clearAndLogout() {
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

  function updateUser(updatedUser: CurrentUserResponses) {
    const currentAvatarUrl = avatarUrl ?? user?.picture ?? null
    setCurrentUser(updatedUser)
    saveUserToSession(updatedUser, currentAvatarUrl)
  }

  useEffect(() => {
    if (isLoading) return

    if (!isAuthenticated || !user?.sub) {
      clearBootstrapped()
      queueMicrotask(() => {
        setBootstrapReady(false)
        setError(null)
        setErrorCode(null)
      })
      return
    }

    if (getBootstrappedUserId() === user.sub) {
      queueMicrotask(() => setBootstrapReady(true))
      return
    }

    clearBootstrapped()
    let cancelled = false
    queueMicrotask(() => {
      setBootstrapReady(false)
      setError(null)
      setErrorCode(null)
    })

    void (async () => {
      try {
        const [claims, accessToken] = await Promise.all([
          getIdTokenClaims(),
          getAccessTokenSilently({
            authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE as string },
          }),
        ])
        const idToken = claims?.__raw
        if (!idToken) throw new Error('Auth0 did not return a raw ID token.')
        const result = await bootstrapCurrentUser(idToken, accessToken)
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
          setErrorCode(hasCode(err) ? err.code : null)
          setError(hasMessage(err) ? err.message : 'Failed to finish account setup.')
        }
      }
    })()

    return () => { cancelled = true }
  }, [attempt, getAccessTokenSilently, getIdTokenClaims, isAuthenticated, isLoading, user?.picture, user?.sub])

  return {
    bootstrapReady,
    currentUser,
    avatarUrl,
    error,
    errorCode,
    retry: () => setAttempt((n) => n + 1),
    updateUser,
    clearAndLogout,
  }
}
