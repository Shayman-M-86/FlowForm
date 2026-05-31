import { useMemo } from 'react'
import createFetchClient from 'openapi-fetch'
import createQueryClient from 'openapi-react-query'
import { useQueryClient, type QueryClient } from '@tanstack/react-query'
import { useAuthHeaders } from '@/auth/headers'
import type { Middleware } from 'openapi-fetch'
import type { paths } from './generated/schema'
import { createPermissionMiddleware } from './permissionMiddleware'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:5000'

type GetAuthHeaders = () => Promise<HeadersInit>

function applyHeaders(request: Request, headers: HeadersInit): void {
  new Headers(headers).forEach((value, key) => {
    request.headers.set(key, value)
  })
}

export function createOpenApiFetchClient(getAuthHeaders?: GetAuthHeaders, queryClient?: QueryClient) {
  const fetchClient = createFetchClient<paths>({ baseUrl: BASE_URL })

  if (queryClient) {
    fetchClient.use(createPermissionMiddleware(queryClient))
  }

  if (getAuthHeaders) {
    const authMiddleware: Middleware = {
      async onRequest({ request }) {
        applyHeaders(request, await getAuthHeaders())
        return request
      },
    }
    fetchClient.use(authMiddleware)
  }

  return fetchClient
}

export function createOpenApiQueryClient(getAuthHeaders?: GetAuthHeaders) {
  return createQueryClient(createOpenApiFetchClient(getAuthHeaders))
}

export type OpenApiFetchClient = ReturnType<typeof createOpenApiFetchClient>
export type OpenApiQueryClient = ReturnType<typeof createOpenApiQueryClient>

export function useOpenApiClient(): OpenApiFetchClient {
  const getAuthHeaders = useAuthHeaders()
  const queryClient = useQueryClient()
  return useMemo(
    () => createOpenApiFetchClient(getAuthHeaders, queryClient),
    [getAuthHeaders, queryClient],
  )
}

export function useOpenApi(): OpenApiQueryClient {
  const getAuthHeaders = useAuthHeaders()
  return useMemo(() => createOpenApiQueryClient(getAuthHeaders), [getAuthHeaders])
}
