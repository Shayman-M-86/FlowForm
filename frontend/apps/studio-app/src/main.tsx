import './index.css'
import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import { Auth0Provider } from '@auth0/auth0-react'
import { QueryProvider } from './app/providers/QueryProvider'
import { RouterProvider } from '@tanstack/react-router'
import { ThemeProvider } from '@flowform/ui'
import { router } from './lib/router'

const auth0Domain = import.meta.env.VITE_AUTH0_DOMAIN as string
const auth0ClientId = import.meta.env.VITE_AUTH0_CLIENT_ID as string
const auth0Audience = import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined

const ReactQueryDevtools = import.meta.env.DEV
  ? lazy(() =>
      import('@tanstack/react-query-devtools').then((m) => ({
        default: () => <m.ReactQueryDevtools initialIsOpen={false} />,
      })),
    )
  : null

// auth0-spa-js throws on insecure origins (plain http on anything but
// localhost), e.g. when opened via a LAN/WSL IP. Bounce to localhost instead.
const needsSecureOrigin = !window.isSecureContext && window.location.hostname !== 'localhost'
if (needsSecureOrigin) {
  const url = new URL(window.location.href)
  url.hostname = 'localhost'
  window.location.replace(url.toString())
}

if (!needsSecureOrigin) createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Auth0Provider
      domain={auth0Domain}
      clientId={auth0ClientId}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: auth0Audience,
        scope: 'openid profile email',
      }}
      cacheLocation="localstorage"
      useRefreshTokens={true}
    >
      <QueryProvider>
        <ThemeProvider>
          <RouterProvider router={router} />
        </ThemeProvider>
        {ReactQueryDevtools && (
          <Suspense>
            <ReactQueryDevtools />
          </Suspense>
        )}
      </QueryProvider>
    </Auth0Provider>
  </StrictMode>,
)
