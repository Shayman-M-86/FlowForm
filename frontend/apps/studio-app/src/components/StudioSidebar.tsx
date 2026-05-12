import { useRef, useState } from "react";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { Badge, Button, CardStack, DropdownMenu } from "@flowform/ui";
import { BRAND } from "@flowform/site-shell";
import "@flowform/site-shell/header.css";
import { useProject } from "@/api/projects";
import { useCurrentUser } from "@/auth/UserContext";

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
function IconLinks() {
  return (
    <svg {...svgProps}>
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
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
function IconLogic() {
  return (
    <svg {...svgProps}>
      <path d="M18 20V10" /><path d="M12 20V4" /><path d="M6 20v-6" />
    </svg>
  );
}
function IconPublish() {
  return (
    <svg {...svgProps}>
      <path d="M12 19V5" /><path d="m5 12 7-7 7 7" />
    </svg>
  );
}
function IconChevron() {
  return <svg {...svgProps}><path d="m6 9 6 6 6-6" /></svg>;
}

// ── Nav item ───────────────────────────────────────────────────────────────

function NavItem({
  to,
  icon,
  label,
  active,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  active: boolean;
}) {
  return (
    <Link
      to={to}
      data-active={active}
      className="sidebar-nav-item ui-action ui-button-ghost justify-start"
    >
      <span className="flex h-4.5 w-4.5 shrink-0 items-center justify-center">{icon}</span>
      <span className="sidebar-nav-item__label">{label}</span>
    </Link>
  );
}

// ── Nav section ────────────────────────────────────────────────────────────

function NavSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="sidebar-nav-section-label hidden px-2 py-1 text-[0.68rem] font-semibold uppercase tracking-wider text-muted-foreground md:block">
        {label}
      </span>
      {children}
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────

function initials(name: string): string {
  return name.split(" ").filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("");
}

// ── Sidebar ────────────────────────────────────────────────────────────────

export function StudioSidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const userRef = useRef<HTMLDivElement>(null);
  const [userOpen, setUserOpen] = useState(false);
  const ctx = useCurrentUser();

  // Parse route segments
  const projectMatch = pathname.match(/^\/projects\/([^/]+)/);
  const surveyMatch = pathname.match(/^\/projects\/([^/]+)\/([^/]+)/);

  const projectSlug = projectMatch ? decodeURIComponent(projectMatch[1]) : null;
  const surveySlug = surveyMatch ? decodeURIComponent(surveyMatch[2]) : null;

  const project = useProject(projectSlug ?? null);
  const projectName = project.data?.name ?? projectSlug ?? undefined;

  const projectBase = projectSlug ? `/projects/${projectSlug}` : null;
  const surveyBase = projectBase && surveySlug ? `${projectBase}/${surveySlug}` : null;

  const isActive = (path: string) => pathname === path || pathname.startsWith(path + "/");

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="site-header__brand justify-center pb-4 md:justify-start">
        <div className="site-header__logo" aria-hidden="true">
          <img src={BRAND.logoSrc} alt="" className="site-header__logo-image" />
        </div>
        <span className="site-header__wordmark hidden md:inline">{BRAND.name}</span>
        <span className="site-header__badge hidden md:inline">Studio</span>
      </div>

      {/* Selected project badge */}
      {projectSlug && (
        <div className="my-1 hidden md:block">
          <Badge
            variant="muted"
            size="sm"
            onClick={() => navigate({ to: "/projects/$slug", params: { slug: projectSlug } })}
            className="max-w-full cursor-pointer gap-1.5"
          >
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-success" />
            <span className="truncate text-muted-foreground">{projectName}</span>
          </Badge>
        </div>
      )}

      <div aria-hidden="true" className="my-4 mt-8 h-px bg-border" />

      <nav aria-label="Main navigation" className="flex flex-col gap-4">

        {/* Projects list — always visible */}
        <NavSection label="Projects">
          <NavItem to="/projects" icon={<IconProjects />} label="All projects" active={pathname === "/projects"} />
        </NavSection>

        {/* Project section — visible when inside a project */}
        {projectBase && (
          <NavSection label={projectName ?? "Project"}>
            <NavItem to={`${projectBase}/`} icon={<IconOverview />} label="Overview" active={pathname === `${projectBase}/` || pathname === projectBase} />
            <NavItem to={`${projectBase}/surveys`} icon={<IconSurveys />} label="Surveys" active={isActive(`${projectBase}/surveys`)} />
            <NavItem to={`${projectBase}/members`} icon={<IconMembers />} label="Members" active={isActive(`${projectBase}/members`)} />
            <NavItem to={`${projectBase}/settings`} icon={<IconSettings />} label="Settings" active={isActive(`${projectBase}/settings`)} />
          </NavSection>
        )}

        {/* Survey section — visible when inside a survey */}
        {surveyBase && (
          <NavSection label="Survey">
            <NavItem to={`${surveyBase}/overview`} icon={<IconOverview />} label="Overview" active={isActive(`${surveyBase}/overview`)} />
            <NavItem to={`${surveyBase}/versions`} icon={<IconVersions />} label="Versions" active={isActive(`${surveyBase}/versions`)} />
            <NavItem to={`${surveyBase}/links`} icon={<IconLinks />} label="Links" active={isActive(`${surveyBase}/links`)} />
            <NavItem to={`${surveyBase}/responses`} icon={<IconResponses />} label="Responses" active={isActive(`${surveyBase}/responses`)} />
            <NavItem to={`${surveyBase}/members`} icon={<IconMembers />} label="Members" active={isActive(`${surveyBase}/members`)} />
            <NavItem to={`${surveyBase}/settings`} icon={<IconSettings />} label="Settings" active={isActive(`${surveyBase}/settings`)} />
          </NavSection>
        )}

        {/* Builder section — visible when inside a survey (version-level tools) */}
        {surveyBase && (
          <>
            <div aria-hidden="true" className="h-px bg-border" />
            <NavSection label="Build">
              <NavItem to={`${surveyBase}/builder`} icon={<IconBuilder />} label="Builder" active={isActive(`${surveyBase}/builder`)} />
              <NavItem to={`${surveyBase}/logic`} icon={<IconLogic />} label="Logic" active={isActive(`${surveyBase}/logic`)} />
              <NavItem to={`${surveyBase}/responses`} icon={<IconResponses />} label="Responses" active={false} />
              <NavItem to={`${surveyBase}/publish`} icon={<IconPublish />} label="Publish" active={isActive(`${surveyBase}/publish`)} />
            </NavSection>
          </>
        )}
      </nav>

      <div className="flex-1" />

      {/* User menu */}
      <CardStack gap="xs" className="pt-4">
        <div ref={userRef}>
          <Button
            variant="ghost"
            size="xs"
            aria-expanded={userOpen}
            onClick={() => setUserOpen((o) => !o)}
            className="w-full justify-center gap-3 py-2 md:justify-between"
          >
            <span className="sidebar-avatar sidebar-avatar--user">
              {ctx?.displayName ? initials(ctx.displayName) : "?"}
            </span>
            <span className="hidden min-w-0 flex-1 flex-col md:flex">
              <span className="truncate text-sm font-semibold text-foreground">{ctx?.displayName}</span>
              <span className="truncate text-xs text-muted-foreground">{ctx?.user.email}</span>
            </span>
            <span className={`hidden text-muted-foreground transition-transform duration-200 md:inline-flex${userOpen ? " rotate-180" : ""}`}>
              <IconChevron />
            </span>
          </Button>
        </div>

        <DropdownMenu
          open={userOpen}
          onClose={() => setUserOpen(false)}
          trigger={userRef}
          align="left"
          direction="up"
          size="auto"
          buttonAlign="left"
          sections={[
            {
              actions: [
                {
                  key: "identity",
                  closeOnSelect: false,
                  content: (
                    <div className="flex w-full min-w-0 flex-col rounded-sm px-3 py-2">
                      <span className="truncate text-sm font-semibold text-foreground">{ctx?.displayName}</span>
                      <span className="truncate text-xs text-muted-foreground">{ctx?.user.email}</span>
                    </div>
                  ),
                },
              ],
            },
            {
              actions: [
                { key: "account", content: "Account settings" },
                { key: "billing", content: "Billing" },
                { key: "sign-out", content: "Sign out", variant: "danger" },
              ],
            },
          ]}
        />
      </CardStack>
    </aside>
  );
}
