// frontend/apps/studio-app/src/api/middleware/authMiddleware.ts
import type { Middleware } from 'openapi-fetch'
import { getTokenGetter } from '../tokenProvider'

export const authMiddleware: Middleware = {
  async onRequest({ request }) {
    const getAccessToken = getTokenGetter()
    if (!getAccessToken) return request
    const token = await getAccessToken()
    request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
}
