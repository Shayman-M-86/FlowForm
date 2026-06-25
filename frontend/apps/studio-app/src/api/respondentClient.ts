import createFetchClient, { type Middleware } from 'openapi-fetch'
import type { paths } from './generated/schema'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:5000'

export const respondentClient = createFetchClient<paths>({
  baseUrl: BASE_URL,
  credentials: 'include',
})

export function createAuthenticatedRespondentClient(getToken: () => Promise<string>) {
  const client = createFetchClient<paths>({
    baseUrl: BASE_URL,
    credentials: 'include',
  })

  const authMiddleware: Middleware = {
    async onRequest({ request }) {
      const token = await getToken()
      request.headers.set('Authorization', `Bearer ${token}`)
      return request
    },
  }
  client.use(authMiddleware)

  return client
}
