import { describe, expect, it, beforeEach, vi } from 'vitest'
import { apiClient } from '@/api/client'
import {
  BACKEND_UNAVAILABLE_CODE,
  BackendUnavailableError,
  bootstrapCurrentUser,
} from '@/auth/bootstrap/api'

vi.mock('@/api/client', () => ({
  apiClient: {
    POST: vi.fn(),
  },
}))

const postBootstrap = vi.mocked(apiClient.POST)

describe('bootstrapCurrentUser', () => {
  beforeEach(() => {
    postBootstrap.mockReset()
  })

  it('returns the bootstrap response when the backend responds successfully', async () => {
    const response = {
      user: {
        id: 'auth0|user-1',
        email: 'user@example.com',
        display_name: 'User Example',
        created_at: '2026-06-08T00:00:00Z',
        updated_at: '2026-06-08T00:00:00Z',
      },
      created: false,
    }
    postBootstrap.mockResolvedValue({ data: response, error: undefined, response: new Response() })

    await expect(bootstrapCurrentUser('id-token', 'access-token')).resolves.toBe(response)
  })

  it('throws a backend unavailable error when the backend does not respond', async () => {
    postBootstrap.mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(bootstrapCurrentUser('id-token', 'access-token')).rejects.toBeInstanceOf(BackendUnavailableError)
    await expect(bootstrapCurrentUser('id-token', 'access-token')).rejects.toHaveProperty('code', BACKEND_UNAVAILABLE_CODE)
    await expect(bootstrapCurrentUser('id-token', 'access-token')).rejects.toHaveProperty(
      'message',
      'FlowForm Studio could not reach the backend services. Please try again later.',
    )
  })

  it('preserves backend setup errors when the backend returns an error response', async () => {
    const setupError = { code: 'AUTH0_CLIENT_ID_NOT_CONFIGURED', message: 'Auth0 is not configured.' }
    postBootstrap.mockResolvedValue({ data: undefined, error: setupError, response: new Response(null, { status: 500 }) })

    await expect(bootstrapCurrentUser('id-token', 'access-token')).rejects.toBe(setupError)
  })

  it('uses a named error class for no-response failures', async () => {
    const networkError = new TypeError('Load failed')
    postBootstrap.mockRejectedValue(networkError)

    try {
      await bootstrapCurrentUser('id-token', 'access-token')
      throw new Error('Expected bootstrapCurrentUser to reject')
    } catch (err) {
      expect(err).toBeInstanceOf(BackendUnavailableError)
      expect((err as Error).cause).toBe(networkError)
    }
  })
})
