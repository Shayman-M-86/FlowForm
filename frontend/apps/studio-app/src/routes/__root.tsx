import { Suspense, lazy } from 'react'
import { createRootRoute, Outlet } from '@tanstack/react-router'

const TanStackRouterDevtools = import.meta.env.DEV
  ? lazy(() =>
      import('@tanstack/router-devtools').then((m) => ({
        default: m.TanStackRouterDevtools,
      })),
    )
  : null

export const Route = createRootRoute({
  component: () => (
    <>
      <Outlet />
      {TanStackRouterDevtools && (
        <Suspense>
          <TanStackRouterDevtools />
        </Suspense>
      )}
    </>
  ),
})
