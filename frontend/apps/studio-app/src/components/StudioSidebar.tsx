import { useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Badge, Button, CardStack, DropdownMenu } from "@flowform/ui";
import { BRAND } from "@flowform/site-shell";
import "@flowform/site-shell/header.css";

type StudioSidebarNavId =
  | "dashboard"
  | "projects"
  | "projects-all"
  | "projects-current"
  | "surveys"
  | "responses"
  | "analytics"
  | "settings";

interface StudioSidebarNavItem {
  id: StudioSidebarNavId;
  label: string;
  icon: StudioSidebarIconName;
}

interface StudioSidebarNavGroup {
  id: string;
  label: string;
  icon: StudioSidebarIconName;
  children: StudioSidebarNavItem[];
}

type StudioSidebarNavEntry =
  | { type: "item"; item: StudioSidebarNavItem }
  | { type: "group"; group: StudioSidebarNavGroup }
  | { type: "divider"; id: string };

interface StudioSidebarProps {
  activeItem?: StudioSidebarNavId;
  projectName?: string;
  projectSlug?: string;
  userName?: string;
  userEmail?: string;
  onNavigate?: (item: StudioSidebarNavItem) => void;
}

type StudioSidebarIconName =
  | "dashboard"
  | "projects"
  | "surveys"
  | "responses"
  | "analytics"
  | "settings"
  | "chevron";

const sidebarNavEntries: StudioSidebarNavEntry[] = [
  { type: "item", item: { id: "dashboard", label: "Dashboard", icon: "dashboard" } },
  {
    type: "group",
    group: {
      id: "projects",
      label: "Projects",
      icon: "projects",
      children: [
        { id: "projects-all", label: "All projects", icon: "projects" },
        { id: "projects-current", label: "This project", icon: "projects" },
      ],
    },
  },
  { type: "item", item: { id: "surveys", label: "Surveys", icon: "surveys" } },
  { type: "item", item: { id: "responses", label: "Responses", icon: "responses" } },
  { type: "item", item: { id: "analytics", label: "Analytics", icon: "analytics" } },
  { type: "divider", id: "main-settings" },
  { type: "item", item: { id: "settings", label: "Settings", icon: "settings" } },
];

const svgProps = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

function SidebarIcon({ name }: { name: StudioSidebarIconName }) {
  if (name === "dashboard") {
    return (
      <svg {...svgProps}>
        <rect x="3" y="3" width="7" height="8" rx="1.5" />
        <rect x="14" y="3" width="7" height="5" rx="1.5" />
        <rect x="14" y="12" width="7" height="9" rx="1.5" />
        <rect x="3" y="15" width="7" height="6" rx="1.5" />
      </svg>
    );
  }
  if (name === "projects") {
    return (
      <svg {...svgProps}>
        <path d="M4 7.5h6l1.6 2H20" />
        <path d="M4 7.5v10A2.5 2.5 0 0 0 6.5 20h11A2.5 2.5 0 0 0 20 17.5v-8" />
      </svg>
    );
  }
  if (name === "surveys") {
    return (
      <svg {...svgProps}>
        <path d="M8 6h10" />
        <path d="M8 12h10" />
        <path d="M8 18h10" />
        <path d="M4 6h.01" />
        <path d="M4 12h.01" />
        <path d="M4 18h.01" />
      </svg>
    );
  }
  if (name === "responses") {
    return (
      <svg {...svgProps}>
        <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z" />
        <path d="M8 9h8" />
        <path d="M8 13h5" />
      </svg>
    );
  }
  if (name === "analytics") {
    return (
      <svg {...svgProps}>
        <path d="M4 19V5" />
        <path d="M4 19h16" />
        <path d="M8 16v-5" />
        <path d="M12 16V8" />
        <path d="M16 16v-9" />
      </svg>
    );
  }
  if (name === "settings") {
    return (
      <svg {...svgProps}>
        <path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5z" />
        <path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.05.05a2 2 0 1 1-2.83 2.83l-.05-.05A1.8 1.8 0 0 0 15 19.4a1.8 1.8 0 0 0-1 .6l-.03.05a2 2 0 1 1-3.94 0L10 20a1.8 1.8 0 0 0-1-.6 1.8 1.8 0 0 0-1.93.41l-.05.05a2 2 0 1 1-2.83-2.83l.05-.05A1.8 1.8 0 0 0 4.6 15a1.8 1.8 0 0 0-.6-1l-.05-.03a2 2 0 1 1 0-3.94L4 10a1.8 1.8 0 0 0 .6-1 1.8 1.8 0 0 0-.41-1.93l-.05-.05a2 2 0 1 1 2.83-2.83l.05.05A1.8 1.8 0 0 0 9 4.6a1.8 1.8 0 0 0 1-.6l.03-.05a2 2 0 1 1 3.94 0L14 4a1.8 1.8 0 0 0 1 .6 1.8 1.8 0 0 0 1.93-.41l.05-.05a2 2 0 1 1 2.83 2.83l-.05.05A1.8 1.8 0 0 0 19.4 9c.2.37.39.7.6 1l.05.03a2 2 0 1 1 0 3.94L20 14c-.21.3-.4.63-.6 1z" />
      </svg>
    );
  }
  return (
    <svg {...svgProps}>
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

export function StudioSidebar({
  activeItem = "surveys",
  projectName = "Acme Health",
  projectSlug,
  userName = "Taylor Morgan",
  userEmail = "taylor@email.com",
  onNavigate,
}: StudioSidebarProps) {
  const navigate = useNavigate();
  const userRef = useRef<HTMLDivElement>(null);
  const [userOpen, setUserOpen] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});

  const toggleGroup = (id: string) =>
    setOpenGroups((prev) => ({ ...prev, [id]: !prev[id] }));

  return (
    <aside className="sidebar">
      <div className="site-header__brand justify-center pb-4 md:justify-start">
        <div className="site-header__logo" aria-hidden="true">
          <img src={BRAND.logoSrc} alt="" className="site-header__logo-image" />
        </div>
        <span className="site-header__wordmark hidden md:inline">{BRAND.name}</span>
        <span className="site-header__badge hidden md:inline">Studio</span>
      </div>

      <div className="my-1 hidden md:block">
        <Badge
          variant="muted"
          size="sm"
          onClick={projectSlug ? () => navigate({ to: "/projects/$slug", params: { slug: projectSlug } }) : undefined}
          className="max-w-full gap-1.5"
        >
          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-success" />
          <span className="truncate text-muted-foreground">{projectName}</span>
        </Badge>
      </div>

      <div aria-hidden="true" className="my-4 mt-8 h-px bg-border" />

      <nav aria-label="Main navigation" className="flex flex-col gap-0.5">
        {sidebarNavEntries.map((entry) => {
          if (entry.type === "divider") {
            return <div key={entry.id} aria-hidden="true" className="my-4 h-px bg-border" />;
          }

          if (entry.type === "group") {
            const { group } = entry;
            const isOpen = !!openGroups[group.id];
            const hasActiveChild = group.children.some((c) => c.id === activeItem);
            return (
              <div key={group.id} className="sidebar-nav-group">
                <Button
                  variant="ghost"
                  size="md"
                  aria-expanded={isOpen}
                  data-active={hasActiveChild && !isOpen}
                  onClick={() => toggleGroup(group.id)}
                  className="sidebar-nav-item justify-start"
                >
                  <span className="flex h-4.5 w-4.5 shrink-0 items-center justify-center">
                    <SidebarIcon name={group.icon} />
                  </span>
                  <span className="sidebar-nav-item__label flex-1">{group.label}</span>
                  <span className={`sidebar-nav-item__label ml-auto transition-transform duration-200 md:inline-flex${isOpen ? " rotate-180" : ""}`}>
                    <SidebarIcon name="chevron" />
                  </span>
                </Button>
                <div className={`sidebar-nav-group__children${isOpen ? " sidebar-nav-group__children--open" : ""}`}>
                  <div className="sidebar-nav-group__inner flex flex-col gap-0.5 pt-0.5">
                    {group.children.map((child) => (
                      <Button
                        key={child.id}
                        variant="ghost"
                        size="md"
                        data-active={child.id === activeItem}
                        onClick={() => onNavigate?.(child)}
                        className="sidebar-nav-item sidebar-nav-item--nested justify-start"
                      >
                        <span className="flex h-4.5 w-4.5 shrink-0 items-center justify-center">
                          <SidebarIcon name={child.icon} />
                        </span>
                        <span className="sidebar-nav-item__label">{child.label}</span>
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            );
          }

          const { item } = entry;
          return (
            <Button
              key={item.id}
              variant="ghost"
              size="md"
              data-active={item.id === activeItem}
              onClick={() => onNavigate?.(item)}
              className="sidebar-nav-item justify-start"
            >
              <span className="flex h-4.5 w-4.5 shrink-0 items-center justify-center">
                <SidebarIcon name={item.icon} />
              </span>
              <span className="sidebar-nav-item__label">{item.label}</span>
            </Button>
          );
        })}
      </nav>

      <div className="flex-1" />

      <CardStack gap="xs" className="pt-4">
        <div ref={userRef}>
          <Button
            variant="ghost"
            size="xs"
            aria-expanded={userOpen}
            onClick={() => setUserOpen((o) => !o)}
            className="w-full justify-center gap-3 py-2 md:justify-between"
          >
            <span className="sidebar-avatar sidebar-avatar--user">{initials(userName)}</span>
            <span className="hidden min-w-0 flex-1 flex-col md:flex">
              <span className="truncate text-sm font-semibold text-foreground">{userName}</span>
              <span className="truncate text-xs text-muted-foreground">{userEmail}</span>
            </span>
            <span className={`hidden text-muted-foreground transition-transform duration-200 md:inline-flex${userOpen ? " rotate-180" : ""}`}>
              <SidebarIcon name="chevron" />
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
                      <span className="truncate text-sm font-semibold text-foreground">{userName}</span>
                      <span className="truncate text-xs text-muted-foreground">{userEmail}</span>
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
