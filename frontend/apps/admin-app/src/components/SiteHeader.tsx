import { Link } from '@tanstack/react-router'
import { useAuth0 } from '@auth0/auth0-react'
import { useTheme, Button } from '@flowform/ui'

const GitHubIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path fillRule="evenodd" clipRule="evenodd" d="M8 0C3.58 0 0 3.58 0 8C0 11.54 2.29 14.53 5.47 15.59C5.87 15.66 6.02 15.42 6.02 15.21C6.02 15.02 6.01 14.39 6.01 13.72C4 14.09 3.48 13.23 3.32 12.78C3.23 12.55 2.84 11.84 2.5 11.65C2.22 11.5 1.82 11.13 2.49 11.12C3.12 11.11 3.57 11.7 3.72 11.94C4.44 13.15 5.59 12.81 6.05 12.6C6.12 12.08 6.33 11.73 6.56 11.53C4.78 11.33 2.92 10.64 2.92 7.58C2.92 6.71 3.23 5.99 3.74 5.43C3.66 5.23 3.38 4.41 3.82 3.31C3.82 3.31 4.49 3.1 6.02 4.13C6.66 3.95 7.34 3.86 8.02 3.86C8.7 3.86 9.38 3.95 10.02 4.13C11.55 3.09 12.22 3.31 12.22 3.31C12.66 4.41 12.38 5.23 12.3 5.43C12.81 5.99 13.12 6.7 13.12 7.58C13.12 10.65 11.25 11.33 9.47 11.53C9.76 11.78 10.01 12.26 10.01 13.01C10.01 14.08 10 14.94 10 15.21C10 15.42 10.15 15.67 10.55 15.59C13.71 14.53 16 11.53 16 8C16 3.58 12.42 0 8 0Z" />
  </svg>
)

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

const navLinkClass = 'text-sm font-medium text-accent-foreground no-underline px-3 py-1.5 rounded-lg transition-colors hover:text-foreground hover:bg-hover-highlight focus-visible:text-foreground focus-visible:bg-hover-highlight'

const iconBtnClass = 'flex items-center justify-center w-[34px] h-[34px] rounded-lg border border-border bg-transparent text-muted-foreground no-underline cursor-pointer p-0 shrink-0 transition-colors hover:text-foreground hover:bg-hover-highlight focus-visible:text-foreground focus-visible:bg-hover-highlight'

export function SiteHeader() {
  const { theme, toggleTheme } = useTheme()
  const { isAuthenticated, loginWithRedirect, logout } = useAuth0()

  return (
    <header className=""
    >
      <div className="">

        {/* Brand */}
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg overflow-hidden shrink-0" aria-hidden="true">
            <img src="/FlowForm_logo.png" alt="" className="w-full h-full object-cover" />
          </div>
          <span className="font-bold text-[1.05rem] tracking-tight text-foreground">FlowForm</span>
          <span className="text-[0.72rem] font-semibold tracking-widest uppercase text-accent border border-accent/30 bg-accent/[0.13] px-[7px] py-[2px] rounded-full">
            Admin
          </span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <nav className="hidden md:flex items-center gap-1 mr-2" aria-label="Primary">
            <Link to="/" className={navLinkClass}>Dashboard</Link>
            <Link to="/projects" className={navLinkClass}>Projects</Link>
            <Link to="/surveys" className={navLinkClass}>Surveys</Link>
          </nav>

          <a
            href="https://github.com/Shayman-M-86/FlowForm"
            target="_blank"
            rel="noopener noreferrer"
            title="View on GitHub"
            className={iconBtnClass}
          >
            <GitHubIcon />
          </a>

          <button
            type="button"
            className={iconBtnClass}
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>

          {isAuthenticated ? (
            <Button
              variant="primary"
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
