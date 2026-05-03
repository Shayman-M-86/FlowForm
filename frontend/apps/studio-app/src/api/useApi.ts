import { useCallback, useMemo } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { isAuthBypassEnabled } from '@/auth/testing'
import * as authApi from './auth'
import * as client from './client'
import type { ApiExecutor, BootstrapUserOut } from './types'

interface Api {
  executor: ApiExecutor
  bootstrapCurrentUser: (idToken: string) => Promise<BootstrapUserOut>
}

export function useApi(): Api {
  const { getAccessTokenSilently } = useAuth0()

  const getAuthHeaders = useCallback(async (): Promise<HeadersInit> => {
    if (isAuthBypassEnabled) return {}

    const token = await getAccessTokenSilently({
      authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE as string },
    })
    return { Authorization: `Bearer ${token}` }
  }, [getAccessTokenSilently])

  return useMemo((): Api => {
    const executor: ApiExecutor = {
      get: <T,>(path: string) => getAuthHeaders().then((h) => client.get<T>(path, h)),
      post: <T,>(path: string, body?: unknown) =>
        getAuthHeaders().then((h) => client.post<T>(path, body, h)),
      patch: <T,>(path: string, body: unknown) =>
        getAuthHeaders().then((h) => client.patch<T>(path, body, h)),
      del: (path: string) => getAuthHeaders().then((h) => client.del(path, h)),
      getWithQuery: <T,>(
        path: string,
        params: Record<string, string | number | boolean | undefined>,
      ) => getAuthHeaders().then((h) => client.getWithQuery<T>(path, params, h)),
    }
    return {
      executor,
      bootstrapCurrentUser: (idToken: string) => authApi.bootstrapCurrentUser(executor, idToken),
    }
  }, [getAuthHeaders])
}
