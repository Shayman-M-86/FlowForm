import { Link, useRouterState } from '@tanstack/react-router'
import { useAuth0 } from '@auth0/auth0-react'
import { useTheme, Button, Tooltip } from '@flowform/ui'
import { ADMIN_NAV_LINKS, BRAND, GITHUB_URL, GitHubIcon } from '@flowform/site-shell'
import '@flowform/site-shell/header.css'

const SunIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
  </svg>
)

const MoonIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
  </svg>
)

export function SiteHeader() {
  const { isAuthenticated, loginWithRedirect, logout } = useAuth0()
  const { theme, toggleTheme } = useTheme()
  const pathname = useRouterState({ select: (s) => s.location.pathname })

  return (
    <header className="site-header" data-site-header>
      <div className="site-header__inner">

        <div className="site-header__brand">
          <div className="site-header__logo" aria-hidden="true">
            <img src={BRAND.logoSrc} alt="" className="site-header__logo-image" />
          </div>
          <span className="site-header__wordmark">{BRAND.name}</span>
          <span className="site-header__badge">Admin</span>
        </div>

        <nav className="site-header__nav" aria-label="Primary">
          {ADMIN_NAV_LINKS.map(({ to, label }) => {
            const isActive = to === '/' ? pathname === '/' : pathname.startsWith(to)
            return (
              <Link
                key={to}
                to={to}
                className="site-header__nav-link"
                data-active={isActive}
              >
                {label}
              </Link>
            )
          })}
        </nav>

        <div className="site-header__actions">
          <Tooltip title="View on GitHub" size="sm">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="site-header__icon-link"
              aria-label="View on GitHub"
            >
              <GitHubIcon />
            </a>
          </Tooltip>

          <button
            type="button"
            className="site-header__theme-toggle"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>

          {isAuthenticated ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
            >
              Sign out
            </Button>
          ) : (
            <Button variant="primary" size="sm" onClick={() => loginWithRedirect()}>
              Sign in
            </Button>
          )}
        </div>

      </div>
    </header>
  )
}
