import { createOpenApiFetchClient } from '../openapi'
import type { BootstrapUserOut } from '../generated/schema'

export async function bootstrapCurrentUser(
  idToken: string,
  accessToken: string,
): Promise<BootstrapUserOut> {
  const client = createOpenApiFetchClient(() =>
    Promise.resolve({ Authorization: `Bearer ${accessToken}` }),
  )
  const { data, error } = await client.POST('/api/v1/auth/bootstrap-user', {
    body: { id_token: idToken },
  })
  if (error) throw error
  return data
}
