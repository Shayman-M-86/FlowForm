import { createRootRoute, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/router-devtools'
import { SiteHeader } from '@/components/SiteHeader'
import { ProtectedApp } from '@/components/auth/ProtectedApp'

export const Route = createRootRoute({
  component: () => (
    <ProtectedApp>
      <SiteHeader />
      <div style={{ paddingTop: '56px' }}>
        <Outlet />
      </div>
      <TanStackRouterDevtools />
    </ProtectedApp>
  ),
})
