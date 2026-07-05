// frontend/apps/studio-app/src/api/client.ts
import createFetchClient from 'openapi-fetch'
import createQueryClient from 'openapi-react-query'
import { authMiddleware } from './middleware/authMiddleware'
import { createPermissionMiddleware } from './middleware/permissionMiddleware'
import { queryClient } from '@/lib/query/queryClient'
import type { paths } from './generated/schema'

export { initApiAuth } from './tokenProvider'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:5000'

export const apiClient = createFetchClient<paths>({ baseUrl: BASE_URL })
apiClient.use(authMiddleware)
apiClient.use(createPermissionMiddleware(queryClient))

export const $api = createQueryClient(apiClient)
