import { Suspense, lazy } from 'react'
import { createRootRoute, Outlet } from '@tanstack/react-router'
import { ProtectedApp } from '@/components/auth/ProtectedApp'
import { StudioSidebar } from '@/components/StudioSidebar'

const TanStackRouterDevtools = import.meta.env.DEV
  ? lazy(() =>
      import('@tanstack/router-devtools').then((m) => ({
        default: m.TanStackRouterDevtools,
      })),
    )
  : null

function AppLayout() {
  return (
    <div className="app-shell flex min-h-screen bg-sidebar">
      <StudioSidebar />
      <main className="app-main flex min-h-screen min-w-0 flex-1 flex-col overflow-x-clip md:border-l border-border md:rounded-l-3xl bg-background md:shadow-lg pt-14 md:pt-0">
        <Outlet />
      </main>
    </div>
  )
}

export const Route = createRootRoute({
  component: () => (
    <ProtectedApp>
      <AppLayout />
      {TanStackRouterDevtools && (
        <Suspense>
          <TanStackRouterDevtools />
        </Suspense>
      )}
    </ProtectedApp>
  ),
})
