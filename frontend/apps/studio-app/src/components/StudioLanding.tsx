import { useEffect, useState } from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import { Button, Card, Spinner, ThemeToggle } from '@flowform/ui'
import { BRAND, STUDIO_AUTH_PARAM, publicSiteUrl, type StudioAuthIntent } from '@flowform/site-shell'
import { ArrowLeft } from 'lucide-react'

function readAuthIntent(): StudioAuthIntent | null {
  const value = new URLSearchParams(window.location.search).get(STUDIO_AUTH_PARAM)
  return value === 'login' || value === 'signup' ? value : null
}

/** Current location without the one-shot `?auth=` param, so it isn't replayed after login. */
function returnToWithoutAuthIntent(): string {
  const params = new URLSearchParams(window.location.search)
  params.delete(STUDIO_AUTH_PARAM)
  const search = params.toString()
  return `${window.location.pathname}${search ? `?${search}` : ''}${window.location.hash}` || '/'
}

/**
 * Logged-out entry point for Studio. Visitors arriving from the public site
 * with `?auth=login|signup` skip straight to Auth0; everyone else gets a
 * simple sign-in screen.
 */
export function StudioLanding() {
  const { loginWithRedirect } = useAuth0()
  const [intent] = useState(readAuthIntent)

  const signIn = () => loginWithRedirect({ appState: { returnTo: returnToWithoutAuthIntent() } })
  const signUp = () =>
    loginWithRedirect({
      appState: { returnTo: returnToWithoutAuthIntent() },
      authorizationParams: { screen_hint: 'signup' },
    })

  useEffect(() => {
    if (!intent) return
    void (intent === 'signup' ? signUp() : signIn())
    // Run once on mount: the intent is a one-shot handoff from the public site.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (intent) {
    return (
      <div className="grid h-dvh place-items-center bg-background p-6">
        <div className="flex items-center gap-3 text-muted-foreground">
          <Spinner size={18} />
          <span className="text-sm">
            {intent === 'signup' ? 'Taking you to sign up…' : 'Taking you to sign in…'}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="studio-landing relative flex h-dvh flex-col overflow-y-auto text-foreground">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>

      <main className="flex flex-1 items-center justify-center px-5 py-16">
        <div className="w-full max-w-sm">
          <Card size="xl" className="studio-landing__card w-full">
            <div className="flex flex-col items-center text-center">
              <img src={BRAND.logoSrc} alt="" className="size-12 rounded-xl" />
              <p className="mt-5 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                {BRAND.name} Studio
              </p>
              <h1 className="mt-2 text-2xl font-semibold tracking-[-0.02em]">Welcome back</h1>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                Sign in to manage your projects, surveys, and responses.
              </p>
            </div>

            <div className="mt-8 flex flex-col gap-3">
              <Button variant="primary" size="lg" className="w-full justify-center" onClick={() => void signIn()}>
                Sign in
              </Button>
              <Button variant="secondary" size="lg" className="w-full justify-center" onClick={() => void signUp()}>
                Create an account
              </Button>
            </div>
          </Card>

          <a
            href={publicSiteUrl('/')}
            className="mt-6 flex items-center justify-center gap-1.5 text-sm text-muted-foreground no-underline hover:text-foreground"
          >
            <ArrowLeft size={14} aria-hidden="true" /> Back to {BRAND.name}
          </a>
        </div>
      </main>
    </div>
  )
}
