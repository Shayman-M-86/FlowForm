import createFetchClient from 'openapi-fetch'
import type { paths } from './generated/schema'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:5000'

export const respondentClient = createFetchClient<paths>({
  baseUrl: BASE_URL,
  credentials: 'include',
})
