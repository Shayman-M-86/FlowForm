import { useRef, useState } from "react";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { useAuth0 } from "@auth0/auth0-react";
import { Badge, Button, DropdownMenu, Tooltip, useTheme } from "@flowform/ui";
import { BRAND } from "@flowform/site-shell";
import "@flowform/site-shell/header.css";
import { useProject } from "@/api/project/projects/hooks";
import { useSurvey } from "@/api/project/surveys/hooks";
import { useHasProjectPermission } from "@/api/project/permissions/hooks";
import { PERMISSION_REQUIRED_TOOLTIP } from "@/api/project/permissions/types";
import { SidebarNotifications } from "@/components/SidebarNotifications";
import { useCurrentUser } from "@/auth/useCurrentUser";
import { isAuthBypassEnabled } from "@/auth/testing";
import { clearActiveProjectSlug } from "@/lib/activeProject";
import { useRenderDebug } from "@/debug/useRenderDebug";

// ── Icons ──────────────────────────────────────────────────────────────────

const svgProps = {
  width: 16,
  height: 16,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

function IconProjects() {
  return (
    <svg {...svgProps}>
      <path d="M4 7.5h6l1.6 2H20" />
      <path d="M4 7.5v10A2.5 2.5 0 0 0 6.5 20h11A2.5 2.5 0 0 0 20 17.5v-8" />
    </svg>
  );
}
function IconSurveys() {
  return (
    <svg {...svgProps}>
      <path d="M8 6h10" /><path d="M8 12h10" /><path d="M8 18h10" />
      <path d="M4 6h.01" /><path d="M4 12h.01" /><path d="M4 18h.01" />
    </svg>
  );
}
function IconOverview() {
  return (
    <svg {...svgProps}>
      <rect x="3" y="3" width="7" height="8" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="15" width="7" height="6" rx="1.5" />
    </svg>
  );
}
function IconVersions() {
  return (
    <svg {...svgProps}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12" />
    </svg>
  );
}
function IconAccess() {
  return (
    <svg {...svgProps}>
      <path d="M12 3 5 6v5c0 4.5 3 8 7 10 4-2 7-5.5 7-10V6l-7-3Z" />
      <path d="M9 12h6" />
      <path d="M12 9v6" />
    </svg>
  );
}
function IconResponses() {
  return (
    <svg {...svgProps}>
      <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z" />
      <path d="M8 9h8" /><path d="M8 13h5" />
    </svg>
  );
}
function IconMembers() {
  return (
    <svg {...svgProps}>
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}
function IconRoles() {
  return (
    <svg {...svgProps}>
      {/* Person */}
      <circle cx="9" cy="7" r="4" />
      <path d="M17 19a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />

      {/* Gear */}
      <circle cx="17.2" cy="17" r="3" />
      <circle cx="17.2" cy="17" r="1" />

      <path d="M17.2 12.8v1" />
      <path d="M17.2 20.2v1" />
      <path d="M13 17h1" />
      <path d="M20.4 17h1" />

      <path d="M14.25 14.05l.75.75" />
      <path d="M19.4 19.2l.75.75" />
      <path d="M14.25 19.95l.75-.75" />
      <path d="M19.4 14.8l.75-.75" />
    </svg>
  );
}


function IconSettings() {
  return (
    <svg {...svgProps}>
      <path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5z" />
      <path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.05.05a2 2 0 1 1-2.83 2.83l-.05-.05A1.8 1.8 0 0 0 15 19.4a1.8 1.8 0 0 0-1 .6l-.03.05a2 2 0 1 1-3.94 0L10 20a1.8 1.8 0 0 0-1-.6 1.8 1.8 0 0 0-1.93.41l-.05.05a2 2 0 1 1-2.83-2.83l.05-.05A1.8 1.8 0 0 0 4.6 15a1.8 1.8 0 0 0-.6-1l-.05-.03a2 2 0 1 1 0-3.94L4 10a1.8 1.8 0 0 0 .6-1 1.8 1.8 0 0 0-.41-1.93l-.05-.05a2 2 0 1 1 2.83-2.83l.05.05A1.8 1.8 0 0 0 9 4.6a1.8 1.8 0 0 0 1-.6l.03-.05a2 2 0 1 1 3.94 0L14 4a1.8 1.8 0 0 0 1 .6 1.8 1.8 0 0 0 1.93-.41l.05-.05a2 2 0 1 1 2.83 2.83l-.05.05A1.8 1.8 0 0 0 19.4 9c.2.37.39.7.6 1l.05.03a2 2 0 1 1 0 3.94L20 14c-.21.3-.4.63-.6 1z" />
    </svg>
  );
}
function IconBuilder() {
  return (
    <svg {...svgProps}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M3 9h18" /><path d="M9 21V9" />
    </svg>
  );
}
function IconCollapse() {
  return <svg {...svgProps}><path d="M11 5l-7 7 7 7"/><path d="M20 5l-7 7 7 7"/></svg>;
}
function IconExpand() {
  return <svg {...svgProps}><path d="M13 5l7 7-7 7"/><path d="M4 5l7 7-7 7"/></svg>;
}
function IconMenu() {
  return <svg {...svgProps} width={20} height={20}><path d="M4 6h16M4 12h16M4 18h16"/></svg>;
}
function IconX() {
  return <svg {...svgProps} width={20} height={20}><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>;
}
function IconChevronDown() {
  return (
    <svg {...svgProps} width={14} height={14}>
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}
function IconSun() {
  return (
    <svg {...svgProps} width={15} height={15}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
}
function IconMoon() {
  return (
    <svg {...svgProps} width={15} height={15}>
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}
function IconLogOut() {
  return (
    <svg {...svgProps} width={15} height={15}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="m16 17 5-5-5-5" />
      <path d="M21 12H9" />
    </svg>
  );
}
function IconUserCog() {
  return (
    <svg {...svgProps} width={15} height={15}>
      <circle cx="9" cy="7" r="4" />
      <path d="M3 21v-2a4 4 0 0 1 4-4h4" />
      <circle cx="18" cy="17" r="2.5" />
      <path d="M18 13.5v1M18 19.5v1M14.5 17h1M20.5 17h1" />
    </svg>
  );
}

// ── User profile menu ──────────────────────────────────────────────────────

function getInitials(displayName: string): string {
  const parts = displayName.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return displayName.slice(0, 2).toUpperCase();
}

function SidebarUserMenu() {
  const ctx = useCurrentUser();
  const { theme, toggleTheme } = useTheme();
  const { logout } = useAuth0();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);

  if (!ctx) return null;

  const displayName = ctx.displayName;
  const email = ctx.user.email;
  const initials = displayName ? getInitials(displayName) : "?";

  const sections = [
    {
      actions: [
        {
          key: "identity",
          closeOnSelect: false,
          content: (
            <div className="flex w-full min-w-0 items-center gap-3 rounded-sm px-3 py-2">
              <span className="flex min-w-0 flex-col gap-0.5">
                <span className="truncate text-sm font-semibold text-foreground">
                  {displayName}
                </span>
                <span className="truncate text-xs text-muted-foreground">
                  {email}
                </span>
              </span>
            </div>
          ),
        },
      ],
    },
    {
      actions: [
        {
          key: "theme",
          closeOnSelect: false,
          content: (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mx-2 my-0.5 flex w-[calc(100%-1rem)] items-center justify-start gap-2"
              onClick={toggleTheme}
            >
              <span className="inline-flex h-[15px] w-[15px] shrink-0 items-center justify-center">
                {theme === "dark" ? <IconSun /> : <IconMoon />}
              </span>
              <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
            </Button>
          ),
        },
        {
          key: "account-settings",
          content: (
            <Link
              to="/account"
              className="mx-2 my-0.5 flex w-[calc(100%-1rem)] items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-transparent-hover"
            >
              <span className="inline-flex h-[15px] w-[15px] shrink-0 items-center justify-center">
                <IconUserCog />
              </span>
              <span>Account settings</span>
            </Link>
          ),
        },
      ],
    },
    {
      actions: [
        {
          key: "sign-out",
          content: (
            <Button
              type="button"
              variant="destructive"
              size="sm"
              className="mx-2 my-0.5 flex w-[calc(100%-1rem)] items-center justify-start "
            >
              <span className="inline-flex h-[15px] w-[15px] shrink-0 items-center justify-center">
                <IconLogOut />
              </span>
              <span>Sign out</span>
            </Button>
          ),
          onSelect: () => {
            clearActiveProjectSlug();
            if (isAuthBypassEnabled) return;
            logout({ logoutParams: { returnTo: window.location.origin } });
          },
        },
      ],
    },
  ];

  return (
    <>
      <Button
        ref={triggerRef}
        type="button"
        variant="ghost"
        size="sm"
        bare
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="User menu"
        className="sidebar-user-button px-0! min-h-0!"
      >
        <span className="sidebar-user-button__avatar">
          {ctx.avatarUrl ? (
            <img
              src={ctx.avatarUrl}
              alt=""
              className="sidebar-user-button__avatar-img"
            />
          ) : (
            <span className="sidebar-user-button__avatar-initials" aria-hidden="true">
              {initials}
            </span>
          )}
        </span>
        <span className="sidebar-user-button__text">
          <span className="sidebar-user-button__name">{displayName}</span>
          <span className="sidebar-user-button__email">{email}</span>
        </span>
        <span
          className="sidebar-user-button__caret"
          data-open={open}
          aria-hidden="true"
        >
          <IconChevronDown />
        </span>
      </Button>
      <DropdownMenu
        open={open}
        onClose={() => setOpen(false)}
        trigger={triggerRef}
        sections={sections}
        size="md"
        align="left"
        direction="up"
        fullscreenAt={420}
      />
    </>
  );
}

// ── Nav item ───────────────────────────────────────────────────────────────

function NavItem({
  to,
  icon,
  label,
  active,
  disabled,
  tooltip,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  active: boolean;
  disabled?: boolean;
  tooltip?: string;
}) {
  const inner = (
    <span className="sidebar-nav-item__icon">
      <span className="flex h-4.5 w-4.5 items-center justify-center">
        {icon}
      </span>
    </span>
  );

  if (disabled) {
    return (
      <Tooltip content={tooltip} placement="right">
        <span className="sidebar-nav-item opacity-40 cursor-not-allowed pointer-events-none">
          {inner}
          <span className="sidebar-nav-item__label">{label}</span>
        </span>
      </Tooltip>
    );
  }

  return (
    <Link to={to} data-active={active} className="sidebar-nav-item">
      {inner}
      <span className="sidebar-nav-item__label">{label}</span>
    </Link>
  );
}

// ── Nav section ────────────────────────────────────────────────────────────

function NavSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="sidebar-nav-section-label">
        {label}
      </span>
      {children}
    </div>
  );
}

// ── Sidebar ────────────────────────────────────────────────────────────────

export function StudioSidebar() {
  useRenderDebug("StudioSidebar");
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('sidebar-collapsed') === 'true');
  const [mobileOpen, setMobileOpen] = useState(false);

  const toggleCollapsed = () => {
    setCollapsed((c) => {
      const next = !c
      localStorage.setItem('sidebar-collapsed', String(next))
      return next
    })
  };

  // Parse route segments
  // Survey context: /projects/$slug/surveys/$surveySlug/*
  const projectMatch = pathname.match(/^\/projects\/([^/]+)/);
  const surveyMatch = pathname.match(/^\/projects\/([^/]+)\/surveys\/([^/]+)/);

  const projectSlug = projectMatch ? decodeURIComponent(projectMatch[1]) : null;
  const surveySlug = surveyMatch ? decodeURIComponent(surveyMatch[2]) : null;

  const project = useProject(projectSlug ?? null);
  const projectName = project.data?.name ?? projectSlug ?? undefined;
  const projectId = project.data?.id ?? null;

  const canViewSurveys    = useHasProjectPermission(projectId, 'survey:view');
  const canManageMembers  = useHasProjectPermission(projectId, 'project:manage_members');
  const canManageRoles    = useHasProjectPermission(projectId, 'project:manage_roles');
  const canEditSettings   = useHasProjectPermission(projectId, 'project:edit');
  const canDeleteProject  = useHasProjectPermission(projectId, 'project:delete');

  const survey = useSurvey(projectSlug, surveySlug);
  const surveyName = survey.data?.title ?? surveySlug ?? undefined;

  const projectBase = projectSlug ? `/projects/${projectSlug}` : null;
  const surveyBase = projectBase && surveySlug ? `${projectBase}/surveys/${surveySlug}` : null;

  const isActive = (path: string) => pathname === path || pathname.startsWith(path + "/");
  const isExactActive = (path: string) => pathname === path || pathname === path + "/";

  return (
    <>
      {/* Mobile top bar — hidden on desktop */}
      <header className="sidebar-topbar">
        <Link to="/projects" className="site-header__brand cursor-pointer">
          <div className="flex items-center gap-2">
            <div className="site-header__logo" aria-hidden="true">
              <img src={BRAND.logoSrc} alt="" className="site-header__logo-image" />
            </div>
            <span className="site-header__wordmark">{BRAND.name}</span>
            <span className="site-header__badge">Studio</span>
          </div>
        </Link>
        <Button
          variant="icon"
          size="md"
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileOpen}
          onClick={() => {
            setMobileOpen((o) => !o);
          
            setTimeout(() => {
              toggleCollapsed();
            }, 200);
          }}
        >
          {mobileOpen ? <IconX /> : <IconMenu />}
        </Button>
        {/* <Button
          variant="icon"
          size="md"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={collapsed}
          onClick={toggleCollapsed}
        >
          {mobileOpen ? <IconX /> : <IconMenu />}
        </Button> */}
      </header>

      {/* Backdrop — mobile only */}
      {mobileOpen && (
        <div
          aria-hidden="true"
          className="sidebar-backdrop"
          onClick={() => setMobileOpen(false)}
        />
      )}

    <aside className="sidebar" data-collapsed={collapsed} data-mobile-open={mobileOpen} onClick={(e) => { if ((e.target as HTMLElement).closest('a')) setMobileOpen(false); }}>
    <div className="sidebar-content px-2">
        {/* Brand */}
        <Link to="/projects" className="site-header__brand w-fit cursor-pointer mb-2 ml-2">
          <div className="flex items-center gap-2.5">
            <div className="site-header__logo" aria-hidden="true">
              <img src={BRAND.logoSrc} alt="" className="site-header__logo-image" />
            </div>
            {!collapsed && <span className="site-header__wordmark">{BRAND.name}</span>}
            {!collapsed && <span className="site-header__badge">Studio</span>}
          </div>
        </Link>

        {/* Project badge + collapse button */}
        <div className={`mt-4 flex items-center ${collapsed ? "justify-center" : "justify-between"}`}>
            <div className="sidebar-project-badge">
            {projectSlug && (
              <Badge
                variant="muted"
                size="sm"
                onClick={() => navigate({ to: "/projects/$slug", params: { slug: projectSlug! } })}
                className="max-w-full gap-1.5"
              >
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-success" />
                <span className="max-w-46 truncate">{projectName}</span>
              </Badge>
            )}
          </div>
          {/* Desktop: collapse/expand toggle */}
          <Button
            variant="icon"
            size="md"
            onClick={toggleCollapsed}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className="hidden md:flex"
          >
            {collapsed ? <IconExpand /> : <IconCollapse />}
          </Button>
        </div>

        <div aria-hidden="true" className="mb-2.75 mt-7.25 h-px bg-border" />

        <nav aria-label="Main navigation" className="flex flex-col gap-2.5">

          {/* Projects list — always visible */}
          <NavSection label="Projects">
            <NavItem to="/projects" icon={<IconProjects />} label="All projects" active={pathname === "/projects"} />
          </NavSection>

          {/* Project section — visible when inside a project */}
          {projectBase && (
            <>
              <div aria-hidden className="h-px bg-border mt-5" />
              <NavSection label={projectName ?? "Project"}>
                <NavItem to={`${projectBase}/surveys`} icon={<IconSurveys />} label="Surveys" active={isExactActive(`${projectBase}/surveys`)} disabled={!canViewSurveys} tooltip={PERMISSION_REQUIRED_TOOLTIP.surveys} />
                <NavItem to={`${projectBase}/members`} icon={<IconMembers />} label="Members" active={isActive(`${projectBase}/members`)} disabled={!canManageMembers} tooltip={PERMISSION_REQUIRED_TOOLTIP.members} />
                <NavItem to={`${projectBase}/roles`} icon={<IconRoles />} label="Roles" active={isActive(`${projectBase}/roles`)} disabled={!canManageRoles} tooltip={PERMISSION_REQUIRED_TOOLTIP.roles} />
                <NavItem to={`${projectBase}/settings`} icon={<IconSettings />} label="Settings" active={isActive(`${projectBase}/settings`)} disabled={!canEditSettings && !canDeleteProject} tooltip={PERMISSION_REQUIRED_TOOLTIP.settings} />
              </NavSection>
            </>
          )}

          {/* Survey section — visible when inside a survey */}
          {surveyBase && (
            <>
              <div aria-hidden className="h-px bg-border mt-5" />
              <NavSection label={surveyName ?? "Survey"}>
              <NavItem to={`${surveyBase}/overview`} icon={<IconOverview />} label="Overview" active={isActive(`${surveyBase}/overview`)} />
              <NavItem to={`${surveyBase}/builder`} icon={<IconBuilder />} label="Builder" active={isActive(`${surveyBase}/builder`)} />
              <NavItem to={`${surveyBase}/versions`} icon={<IconVersions />} label="Versions" active={isActive(`${surveyBase}/versions`)} />
              <NavItem to={`${surveyBase}/access`} icon={<IconAccess />} label="Access" active={isActive(`${surveyBase}/access`)} />
              <NavItem to={`${surveyBase}/responses`} icon={<IconResponses />} label="Responses" active={isActive(`${surveyBase}/responses`)} />
              <NavItem to={`${surveyBase}/settings`} icon={<IconSettings />} label="Settings" active={isActive(`${surveyBase}/settings`)} />
              </NavSection>
            </>
          )}

        </nav>
      </div>

      <div className="flex-1" />

      <div className="px-2">
        <SidebarNotifications collapsed={collapsed} />
      </div>

      <div aria-hidden="true" className="sidebar-user-divider" />
      <div className="px-2">
        <SidebarUserMenu />
      </div>
    </aside>
    </>
  );
}
