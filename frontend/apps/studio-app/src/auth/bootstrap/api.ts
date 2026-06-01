// frontend/apps/studio-app/src/auth/bootstrap/api.ts
import { apiClient } from '@/api/client'
import type { BootstrapUserResponses } from '@/api/generated/schema'

export async function bootstrapCurrentUser(
  idToken: string,
  accessToken: string,
): Promise<BootstrapUserResponses> {
  const { data, error } = await apiClient.POST('/api/v1/auth/bootstrap-user', {
    body: { id_token: idToken },
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (error) throw error
  return data
}
