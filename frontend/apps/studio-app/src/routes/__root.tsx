import { Suspense, lazy } from 'react'
import { createRootRoute, Outlet, redirect } from '@tanstack/react-router'

const TanStackRouterDevtools = import.meta.env.DEV
  ? lazy(() =>
      import('@tanstack/router-devtools').then((m) => ({
        default: m.TanStackRouterDevtools,
      })),
    )
  : null

export const Route = createRootRoute({
  beforeLoad: ({ location }) => {
    const returnPath = sessionStorage.getItem('ff:invitation-return')
    if (returnPath && location.pathname === '/') {
      sessionStorage.removeItem('ff:invitation-return')
      throw redirect({ to: returnPath })
    }
  },
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
