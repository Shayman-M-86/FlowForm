import { Suspense, lazy } from 'react'
import { createRootRoute, Outlet } from '@tanstack/react-router'
import { ProtectedApp } from '@/app/ProtectedApp'
import { StudioSidebar } from '@/components/StudioSidebar'
import { useRenderDebug } from '@/debug/useRenderDebug'

const TanStackRouterDevtools = import.meta.env.DEV
  ? lazy(() =>
      import('@tanstack/router-devtools').then((m) => ({
        default: m.TanStackRouterDevtools,
      })),
    )
  : null

function AppLayout() {
  useRenderDebug('AppLayout')
  return (
    <div className="app-shell flex min-h-screen bg-sidebar">
      <StudioSidebar />
      <main className="app-main">
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
