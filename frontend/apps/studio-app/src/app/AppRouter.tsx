import { useAuth0 } from '@auth0/auth0-react'
import { RouterProvider } from '@tanstack/react-router'
import { router } from '@/lib/router'

// Auth0 returns to redirect_uri (the origin) with ?code&state. The router's
// index redirect (/ -> /projects) runs in a child effect, before Auth0Provider
// reads those params, and would strip them, leaving the user signed out with no
// error. On a callback URL, mount the router only after Auth0 has handled it.
// Evaluated once at load, before the router or Auth0 can rewrite the URL.
const initialParams = new URLSearchParams(window.location.search)
const isAuthCallback = (initialParams.has('code') || initialParams.has('error')) && initialParams.has('state')

export function AppRouter() {
  const { isLoading } = useAuth0()
  if (isAuthCallback && isLoading) return null
  return <RouterProvider router={router} />
}
