import { useRef, useState } from 'react'
import { Link, useRouterState } from '@tanstack/react-router'
import { useAuth0 } from '@auth0/auth0-react'
import { useTheme, DropdownMenu, Button, Badge } from '@flowform/ui'
import { STUDIO_NAV_LINKS, BRAND } from '@flowform/site-shell'
import { useCurrentUser } from '@/auth/UserContext'
import { isAuthBypassEnabled } from '@/auth/testing'
import { useProject } from '@/api/projects'
import { clearActiveProjectSlug, getActiveProjectSlug } from '@/lib/activeProject'
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

function hasBootstrappedSession(): boolean {
  try {
    return !!window.sessionStorage.getItem('flowform.bootstrapped')
  } catch {
    return false
  }
}

function getInitials(displayName: string): string {
  const parts = displayName.trim().split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  return displayName.slice(0, 2).toUpperCase()
}

function UserAvatar() {
  const ctx = useCurrentUser()
  const avatarUrl = ctx?.avatarUrl ?? null
  const displayName = ctx?.displayName ?? ''
  const initials = displayName ? getInitials(displayName) : '?'

  return avatarUrl ? (
    <img src={avatarUrl} alt={displayName} className="site-header__avatar-img" />
  ) : (
    <span className="site-header__avatar-initials" aria-hidden="true">
      {initials}
    </span>
  )
}

export function SiteHeader() {
  const { isAuthenticated, isLoading, loginWithRedirect, logout } = useAuth0()
  const { theme, toggleTheme } = useTheme()
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const projectSlug = pathname.match(/^\/projects\/([^/]+)/)?.[1] ?? null
  const activeProjectSlug = projectSlug ? decodeURIComponent(projectSlug) : getActiveProjectSlug()
  const project = useProject(activeProjectSlug)
  const ctx = useCurrentUser()
  const avatarRef = useRef<HTMLButtonElement>(null)
  const [menuOpen, setMenuOpen] = useState(false)

  const showAsAuthenticated =
    isAuthBypassEnabled || isAuthenticated || (isLoading && hasBootstrappedSession())

  const menuSections = [
    ...(ctx
      ? [
          {
            actions: [
              {
                key: 'identity',
                closeOnSelect: false,
                content: (
                  <div className="flex w-full min-w-0 items-center justify-between gap-3 rounded-sm px-3 py-2">
                    <span className="flex min-w-0 flex-col gap-0.5">
                      <span className="truncate text-base font-semibold text-foreground">
                        {ctx.displayName}
                      </span>
                      <span className="truncate text-xs text-muted-foreground">
                        {ctx.user.email}
                      </span>
                    </span>
  
                    <Badge variant="success" size="xs">
                      Active
                    </Badge>
                  </div>
                ),
              },
            ],
          },
        ]
      : []),
    {
      actions: [
        {
          key: 'switch-project',
          content: (
            <Link
              to="/projects"
              role="menuitem"
              className="mx-3 mt-4 mb-2 flex w-[calc(100%-1.5rem)] items-center justify-center rounded-sm px-3 py-2 text-sm font-semibold text-foreground no-underline transition-colors hover:bg-muted focus-visible:bg-muted focus-visible:outline-none"
            >
              Switch project
            </Link>
          ),
        },
        {
          key: 'theme',
          closeOnSelect: false,
          content: (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="mx-3 mt-1 mb-2 flex w-[calc(100%-1.5rem)] items-center justify-center"
              onClick={toggleTheme}
            >
              <span className="flex items-center gap-2">
                <span className="inline-flex h-[15px] w-[15px] shrink-0 items-center justify-center">
                  {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
                </span>
                <span>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
              </span>
            </Button>
          ),
        },
        {
          key: 'sign-out',
          content: (
            <Button
              type="button"
              variant="danger"
              size="sm"
              className="mx-3 mt-1 mb-4 flex w-[calc(100%-1.5rem)] items-center justify-center"
            >
              Sign out
            </Button>
          ),
          onSelect: () => {
            clearActiveProjectSlug()
            if (isAuthBypassEnabled) return
            logout({ logoutParams: { returnTo: window.location.origin } })
          },
        },
      ],
    },
  ]

  return (
    <>
    <style>{`
      .site-header { backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); }
      .site-header__project {
        display: inline-flex;
        min-width: 0;
        max-width: min(34vw, 360px);
        align-items: center;
        gap: 0.5rem;
        border: 1px solid color-mix(in srgb, var(--foreground) 12%, transparent);
        border-radius: 999px;
        background: color-mix(in srgb, var(--background) 76%, transparent);
        padding: 0.35rem 0.75rem;
        box-shadow: 0 8px 24px color-mix(in srgb, black 8%, transparent);
        text-decoration: none;
        transition: border-color 150ms ease, background 150ms ease, box-shadow 150ms ease;
      }
      .site-header__project:hover,
      .site-header__project:focus-visible {
        border-color: color-mix(in srgb, var(--foreground) 24%, transparent);
        background: color-mix(in srgb, var(--background) 88%, transparent);
        box-shadow: 0 10px 28px color-mix(in srgb, black 10%, transparent);
        outline: none;
      }
      .site-header__project-dot {
        height: 0.5rem;
        width: 0.5rem;
        flex: 0 0 auto;
        border-radius: 999px;
        background: var(--success, #16a34a);
      }
      .site-header__project-label {
        flex: 0 0 auto;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0;
        line-height: 1;
        text-transform: uppercase;
        color: var(--muted-foreground);
      }
      .site-header__project-name {
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 0.86rem;
        font-weight: 700;
        line-height: 1.1;
        color: var(--foreground);
      }
      @media (max-width: 720px) {
        .site-header__project {
          max-width: 44vw;
          padding-inline: 0.6rem;
        }
        .site-header__project-label {
          display: none;
        }
      }
    `}</style>
    <header className="site-header" data-site-header>
      <div className="site-header__inner">

        <div className="site-header__brand">
          <div className="site-header__logo" aria-hidden="true">
            <img src={BRAND.logoSrc} alt="" className="site-header__logo-image" />
          </div>
          <span className="site-header__wordmark">{BRAND.name}</span>
          <span className="site-header__badge">Studio</span>
        </div>

        <nav className="site-header__nav" aria-label="Primary">
          {STUDIO_NAV_LINKS.map(({ to, label }) => {
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

        {activeProjectSlug && (
          <Link
            to="/projects/$slug"
            params={{ slug: activeProjectSlug }}
            className="site-header__project"
            aria-label={`Manage selected project: ${project.data?.name ?? 'current project'}`}
          >
            <span className="site-header__project-dot" aria-hidden="true" />
            <span className="site-header__project-label">Project</span>
            <span className="site-header__project-name">
              {project.data?.name ?? (project.isLoading ? 'Loading project' : 'Project unavailable')}
            </span>
          </Link>
        )}

        <div className="site-header__actions">



          {showAsAuthenticated ? (
            <>
              <button
                ref={avatarRef}
                type="button"
                className="site-header__avatar-btn"
                onClick={() => setMenuOpen((o) => !o)}
                aria-label="User menu"
                aria-haspopup="menu"
                aria-expanded={menuOpen}
              >
                <UserAvatar />
              </button>
              <DropdownMenu
                open={menuOpen}
                onClose={() => setMenuOpen(false)}
                trigger={avatarRef}
                sections={menuSections}
                size="md"
                align="right"
                fullscreenAt={420}
              />
            </>
          ) : (
            <button
              type="button"
              className="site-header__cta"
              onClick={() => loginWithRedirect()}
            >
              Sign in
            </button>
          )}
        </div>

      </div>
    </header>
    </>
  )
}
