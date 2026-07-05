import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { queryClient } from '@/lib/query/queryClient'
import { localQueryPersister, sessionQueryPersister } from '@/lib/query/queryPersistence'

void localQueryPersister.persisterGc()
void sessionQueryPersister.persisterGc()

export function QueryProvider({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}
