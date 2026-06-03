import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      // Never retry 429s — retrying immediately would double the request burst.
      retry: (failureCount, error) => {
        if ((error as { code?: string })?.code === 'RATE_LIMIT_EXCEEDED') return false
        return failureCount < 1
      },
    },
  },
})
