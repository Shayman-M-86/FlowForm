import { createRootRoute, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'
import { ProtectedApp } from '@/components/auth/ProtectedApp'
import { StudioSidebar } from '@/components/StudioSidebar'

function AppLayout() {
  return (
    <div className="flex min-h-screen bg-sidebar">
      <StudioSidebar />
      <main className="flex min-h-screen min-w-0 flex-1 flex-col overflow-x-clip border-l border-border rounded-l-3xl bg-background shadow-lg">
        <Outlet />
      </main>
    </div>
  )
}

export const Route = createRootRoute({
  component: () => (
    <ProtectedApp>
      <AppLayout />
      <TanStackRouterDevtools />
    </ProtectedApp>
  ),
})
