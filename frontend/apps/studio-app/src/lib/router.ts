import { createRouter } from '@tanstack/react-router'
import { routeTree } from '@/routeTree.gen'
import { queryClient } from './query/queryClient'

export const router = createRouter({
  routeTree,
  context: { queryClient },
  defaultPreload: 'intent',
  scrollRestoration: true,
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
