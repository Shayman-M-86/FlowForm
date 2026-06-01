import createFetchClient, { type Middleware } from 'openapi-fetch'
import createQueryClient from 'openapi-react-query'
import { isAuthBypassEnabled } from '@/auth/testing'
import { createPermissionMiddleware } from './permissionMiddleware'
import { queryClient } from '@/lib/queryClient'
import type { paths } from './generated/schema'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:5000'

// Holds the token getter once Auth0 is ready. Set via initApiAuth().
let getAccessToken: (() => Promise<string>) | null = null

export function initApiAuth(getter: () => Promise<string>): void {
  getAccessToken = getter
}

const authMiddleware: Middleware = {
  async onRequest({ request }) {
    if (isAuthBypassEnabled || !getAccessToken) return request
    const token = await getAccessToken()
    request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
}

export const apiClient = createFetchClient<paths>({ baseUrl: BASE_URL })
apiClient.use(authMiddleware)
apiClient.use(createPermissionMiddleware(queryClient))

export const $api = createQueryClient(apiClient)

export class ApiRequestError extends Error {
  public readonly status: number
  public readonly code: string
  public readonly error: { code: string; message: string; details?: unknown }

  constructor(status: number, error: { code: string; message: string; details?: unknown }) {
    super(error.message)
    this.name = 'ApiRequestError'
    this.status = status
    this.code = error.code
    this.error = error
  }
}
