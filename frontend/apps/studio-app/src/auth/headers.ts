import { useCallback } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { isAuthBypassEnabled } from './testing'

export function useAuthHeaders(): () => Promise<HeadersInit> {
  const { getAccessTokenSilently } = useAuth0()

  return useCallback(async (): Promise<HeadersInit> => {
    if (isAuthBypassEnabled) return {}

    const token = await getAccessTokenSilently({
      authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE as string },
    })
    return { Authorization: `Bearer ${token}` }
  }, [getAccessTokenSilently])
}
