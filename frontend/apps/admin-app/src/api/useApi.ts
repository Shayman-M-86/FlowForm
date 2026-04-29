import { useCallback, useMemo } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import * as authApi from './auth'
import * as client from './client'
import type { ApiExecutor } from './types'

export function useApi() {
  const { getAccessTokenSilently } = useAuth0()

  const getAuthHeaders = useCallback(async (): Promise<HeadersInit> => {
    const token = await getAccessTokenSilently({
      authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE as string },
    })
    return { Authorization: `Bearer ${token}` }
  }, [getAccessTokenSilently])

  const executor = useMemo(
    (): ApiExecutor => ({
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
    }),
    [getAuthHeaders],
  )

  return useMemo(
    () => ({
      bootstrapCurrentUser: (idToken: string) => authApi.bootstrapCurrentUser(executor, idToken),
    }),
    [executor],
  )
}
