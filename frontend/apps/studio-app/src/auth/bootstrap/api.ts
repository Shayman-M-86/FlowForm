// frontend/apps/studio-app/src/auth/bootstrap/api.ts
import { apiClient } from '@/api/client'
import type { BootstrapUserResponses } from '@/api/generated/schema'

export const BACKEND_UNAVAILABLE_CODE = 'BACKEND_UNAVAILABLE'

const BACKEND_UNAVAILABLE_MESSAGE =
  'FlowForm Studio could not reach the backend services. Please try again later.'

export class BackendUnavailableError extends Error {
  public readonly code = BACKEND_UNAVAILABLE_CODE

  constructor(cause: unknown) {
    super(BACKEND_UNAVAILABLE_MESSAGE, { cause })
    this.name = 'BackendUnavailableError'
  }
}

function hasMessage(err: unknown): err is { message: string } {
  return typeof err === 'object' && err !== null && 'message' in err && typeof (err as Record<string, unknown>).message === 'string'
}

function isBackendNetworkError(err: unknown): boolean {
  if (err instanceof TypeError) return true
  if (typeof DOMException !== 'undefined' && err instanceof DOMException && err.name === 'NetworkError') {
    return true
  }
  return hasMessage(err) && /failed to fetch|networkerror|load failed/i.test(err.message)
}

export async function bootstrapCurrentUser(
  idToken: string,
  accessToken: string,
): Promise<BootstrapUserResponses> {
  try {
    const { data, error } = await apiClient.POST('/api/v1/account/bootstrap-user', {
      body: { id_token: idToken },
      headers: { Authorization: `Bearer ${accessToken}` },
    })
    if (error) throw error
    return data
  } catch (err) {
    if (isBackendNetworkError(err)) throw new BackendUnavailableError(err)
    throw err
  }
}
