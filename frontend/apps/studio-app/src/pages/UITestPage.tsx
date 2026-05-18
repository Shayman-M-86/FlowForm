import { useState } from "react";
import { useRenderDebug } from "@/debug/useRenderDebug";
import {
  Button,
  ButtonGroup,
  Card,
  CardRow,
  CardStack,
  Input,
  LargeInput,
  Select,
  Tooltip,
  Toggle,
  Spinner,
  Modal,
  NumberStepper,
  NumberStepperGroup,
  ThemeToggle,
  Badge,
  TabSelector,
  Table,
  type TableColumn,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  PermissionTag,
} from "@flowform/ui";
import { ChevronDown } from "lucide-react";
import {
  mockProjectMembers,
  type MockProjectMember,
} from "@/api/mockData";

const buttonVariants = ["primary", "secondary", "danger", "ghost"] as const;
const buttonSizes = ["md", "sm", "xs"] as const;

const buttonVariantLabels: Record<(typeof buttonVariants)[number], string> = {
  primary: "Primary",
  secondary: "Secondary",
  danger: "Danger",
  ghost: "Ghost",
};

const buttonSizeLabels: Record<(typeof buttonSizes)[number], string> = {
  md: "MD",
  sm: "SM",
  xs: "XS",
};

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-12 md:mb-16">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function TestGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-5 md:grid-cols-[repeat(auto-fit,minmax(280px,1fr))]">
      {children}
    </div>
  );
}

function TestCard({
  title,
  children,
}: {
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <Card size="md">
      <CardStack gap="sm">
        {title ? <h3 className="m-0 text-[0.9rem] font-semibold tracking-[0.04em] uppercase ">{title}</h3> : null}
        {children}
      </CardStack>
    </Card>
  );
}

function InlineStack({ children }: { children: React.ReactNode }) {
  return <CardRow gap="xs">{children}</CardRow>;
}

function WideStack({ children }: { children: React.ReactNode }) {
  return <CardRow gap="sm">{children}</CardRow>;
}

// ── Survey member role variants ──────────────────────────────────────────────
// Three different ways to present project-role + survey-role-override
// for the survey members table. All three render the same five mock members
// so they can be compared directly. See SurveyMembersTab.tsx for the current
// production version.

type SurveyRole = "Manager" | "Publisher" | "Editor" | "Viewer";

const SURVEY_ROLE_OVERRIDES: Record<number, SurveyRole> = {
  2: "Manager",
  4: "Editor",
};

const PROJECT_ROLE_TO_SURVEY_ROLE: Record<MockProjectMember["role"], SurveyRole> = {
  Owner: "Manager",
  Editor: "Editor",
  Viewer: "Viewer",
};

const SURVEY_ROLE_PERMISSIONS: Record<SurveyRole, string[]> = {
  Manager: ["Manage survey", "Publish", "Edit", "View responses"],
  Publisher: ["Publish", "Edit", "View responses"],
  Editor: ["Edit", "Preview"],
  Viewer: ["View"],
};

const PERMISSION_TOOLTIPS: Record<string, string> = {
  "Manage survey": "Can manage survey settings, member access, and admin actions.",
  Publish: "Can publish drafts and update what respondents can access.",
  Edit: "Can change survey questions and structure.",
  "View responses": "Can view collected responses and summaries.",
  Preview: "Can preview draft content before it is published.",
  View: "Can view the survey setup and details.",
};

const PROJECT_ROLE_BADGE: Record<MockProjectMember["role"], "default" | "default" | "default"> = {
  Owner: "default",
  Editor: "default",
  Viewer: "default",
};

const SURVEY_ROLE_BADGE: Record<SurveyRole, "accent" | "warning" | "default" | "muted"> = {
  Manager: "accent",
  Publisher: "warning",
  Editor: "default",
  Viewer: "muted",
};

function permissionsGained(projectRole: MockProjectMember["role"], override: SurveyRole): string[] {
  const baseline = new Set(SURVEY_ROLE_PERMISSIONS[PROJECT_ROLE_TO_SURVEY_ROLE[projectRole]]);
  return SURVEY_ROLE_PERMISSIONS[override].filter((p) => !baseline.has(p));
}

interface MemberRow extends MockProjectMember {
  override?: SurveyRole;
  effective: SurveyRole;
}

function buildMemberRows(): MemberRow[] {
  return mockProjectMembers.map((m) => {
    const override = SURVEY_ROLE_OVERRIDES[m.id];
    return {
      ...m,
      override,
      effective: override ?? PROJECT_ROLE_TO_SURVEY_ROLE[m.role],
    };
  });
}

function VariantEffectivePermissions() {
  const rows = buildMemberRows();
  const columns: TableColumn<MemberRow>[] = [
    {
      key: "member",
      header: "Member",
      minWidth: 180,
      cell: (m) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">{m.name}</p>
          <p className="truncate text-xs text-muted-foreground">{m.email}</p>
        </div>
      ),
    },
    {
      key: "permissions",
      header: "Can do on this survey",
      minWidth: 280,
      cell: (m) => (
        <div className="flex flex-wrap gap-1.5">
          {SURVEY_ROLE_PERMISSIONS[m.effective].map((p) => (
            <PermissionTag key={p} label={p} tooltip={PERMISSION_TOOLTIPS[p] ?? p} />
          ))}
        </div>
      ),
    },
    {
      key: "source",
      header: "Source",
      minWidth: 220,
      cell: (m) => (
        <div className="flex flex-col gap-0.5 text-xs">
          <span className="text-muted-foreground">
            via <span className="text-foreground">{m.role}</span> (project)
            {m.override && (
              <>
                {" + "}
                <span className="text-foreground">{m.override}</span> (survey)
              </>
            )}
          </span>
          {m.override && (
            <span className="text-[0.68rem] text-accent-foreground">
              +{permissionsGained(m.role, m.override).length} permission(s) from override
            </span>
          )}
        </div>
      ),
    },
  ];

  return <Table columns={columns} rows={rows} getRowKey={(m) => m.id} />;
}

const ADDITIVE_GRANT_LABEL: Record<SurveyRole, string> = {
  Manager: "+ Manage",
  Publisher: "+ Publish",
  Editor: "+ Edit",
  Viewer: "",
};

function VariantAdditiveNaming() {
  const rows = buildMemberRows();
  const columns: TableColumn<MemberRow>[] = [
    {
      key: "member",
      header: "Member",
      minWidth: 180,
      cell: (m) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">{m.name}</p>
          <p className="truncate text-xs text-muted-foreground">{m.email}</p>
        </div>
      ),
    },
    {
      key: "project-role",
      header: "Project role",
      minWidth: 110,
      cell: (m) => (
        <Badge variant={PROJECT_ROLE_BADGE[m.role]} size="xs">
          {m.role}
        </Badge>
      ),
    },
    {
      key: "survey-grant",
      header: "Survey grant",
      minWidth: 140,
      cell: (m) => {
        const gained = m.override ? permissionsGained(m.role, m.override) : [];
        if (!m.override || gained.length === 0) {
          return <span className="text-xs text-muted-foreground">—</span>;
        }
        return (
          <Badge variant="warning" size="xs">
            {ADDITIVE_GRANT_LABEL[m.override] || `+ ${m.override}`}
          </Badge>
        );
      },
    },
    {
      key: "effective",
      header: "Effective permissions",
      minWidth: 260,
      cell: (m) => {
        const gained = m.override ? permissionsGained(m.role, m.override) : [];
        return (
          <div className="flex flex-wrap gap-1.5">
            {SURVEY_ROLE_PERMISSIONS[m.effective].map((p) => {
              const isGained = gained.includes(p);
              return (
                <Badge key={p} variant={isGained ? "warning" : "default"} size="xs">
                  {p}
                </Badge>
              );
            })}
          </div>
        );
      },
    },
  ];

  return <Table className="w-[clamp(16rem,50vw,48rem)]" columns={columns} rows={rows} getRowKey={(m) => m.id} />;
}

function VariantCollapsedDefault() {
  const rows = buildMemberRows();
  const columns: TableColumn<MemberRow>[] = [
    {
      key: "member",
      header: "Member",
      minWidth: 180,
      cell: (m) => (
        <div className={`min-w-0 ${m.override ? "border-l-2 border-accent pl-2" : ""}`}>
          <p className="truncate text-sm font-semibold text-foreground">{m.name}</p>
          <p className="truncate text-xs text-muted-foreground">{m.email}</p>
        </div>
      ),
    },
    {
      key: "role",
      header: "Role",
      minWidth: 240,
      cell: (m) => (
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant={PROJECT_ROLE_BADGE[m.role]} size="xs">
            {m.role}
          </Badge>
          {m.override && (
            <>
              <span aria-hidden className="text-xs text-muted-foreground">+</span>
              <Badge variant={SURVEY_ROLE_BADGE[m.override]} size="xs">
                {m.override}
              </Badge>
              <span className="rounded bg-accent/15 px-1.5 py-0.5 text-[0.62rem] font-semibold uppercase tracking-wider text-accent-foreground">
                Override
              </span>
            </>
          )}
        </div>
      ),
    },
    {
      key: "effective",
      header: "Effective access",
      minWidth: 260,
      cell: (m) => {
        if (!m.override) {
          const count = SURVEY_ROLE_PERMISSIONS[m.effective].length;
          return (
            <span className="text-xs text-muted-foreground">
              Inherits {count} permission{count === 1 ? "" : "s"} from project role
            </span>
          );
        }
        const gained = permissionsGained(m.role, m.override);
        return (
          <div className="flex flex-col gap-1">
            <span className="text-[0.68rem] font-semibold uppercase tracking-wider text-accent-foreground">
              Gains on this survey
            </span>
            <div className="flex flex-wrap gap-1.5">
              {gained.length === 0 ? (
                <span className="text-xs text-muted-foreground">No additional permissions</span>
              ) : (
                gained.map((p) => (
                  <PermissionTag key={p} label={p} tooltip={PERMISSION_TOOLTIPS[p] ?? p} />
                ))
              )}
            </div>
          </div>
        );
      },
    },
  ];

  return <Table columns={columns} rows={rows} getRowKey={(m) => m.id} />;
}

export function UITestPage() {
  useRenderDebug("UITestPage");
  // ── Table test data ──────────────────────────────────────────────────────────

  interface SampleRow {
    id: number
    name: string
    status: "Published" | "Draft" | "Archived"
    responses: number
    version: string
    updatedAt: string
  }

  const TABLE_ROWS: SampleRow[] = [
    { id: 1, name: "Customer onboarding feedback", status: "Published", responses: 128, version: "v2", updatedAt: "Apr 30, 2026" },
    { id: 2, name: "Product discovery intake",     status: "Draft",     responses: 0,   version: "v1", updatedAt: "Apr 28, 2026" },
    { id: 3, name: "Quarterly account health",     status: "Published", responses: 54,  version: "v1", updatedAt: "Apr 25, 2026" },
    { id: 4, name: "Sleep study eligibility",      status: "Archived",  responses: 311, version: "v4", updatedAt: "Mar 10, 2026" },
  ]

  const STATUS_VARIANT: Record<SampleRow["status"], "success" | "muted" | "warning"> = {
    Published: "success",
    Draft: "muted",
    Archived: "warning",
  }

  const ALL_COLUMNS: TableColumn<SampleRow>[] = [
    {
      key: "name",
      header: "Survey",
      minWidth: 200,
      cell: (row) => <span className="font-medium text-foreground">{row.name}</span>,
    },
    {
      key: "status",
      header: "Status",
      minWidth: 90,
      cell: (row) => <Badge variant={STATUS_VARIANT[row.status]} size="xs">{row.status}</Badge>,
    },
    {
      key: "version",
      header: "Version",
      minWidth: 70,
      cell: (row) => <span className="text-muted-foreground">{row.version}</span>,
    },
    {
      key: "responses",
      header: "Responses",
      minWidth: 90,
      cell: (row) => <span className="tabular-nums">{row.responses}</span>,
    },
    {
      key: "updatedAt",
      header: "Last updated",
      minWidth: 130,
      cell: (row) => <span className="text-muted-foreground">{row.updatedAt}</span>,
    },
  ]

  const HIDDEN_VERSION_COLUMNS: TableColumn<SampleRow>[] = ALL_COLUMNS.map((col) =>
    col.key === "version" ? { ...col, visible: false } : col,
  )

  const [tabActive, setTabActive] = useState("overview");
  const [tabOverflowActive, setTabOverflowActive] = useState("surveys");

  const TAB_CONTENT: Record<string, { heading: string; body: string }> = {
    overview:   { heading: "Overview", body: "High-level summary of the project. Shows key stats, recent activity, and health indicators." },
    surveys:    { heading: "Surveys", body: "All surveys belonging to this project. Create, publish, pause, or archive surveys from here." },
    members:    { heading: "Members", body: "People who have access to this project. Invite new members and manage their roles." },
    roles:      { heading: "Roles", body: "Define permission sets that can be assigned to members. Includes built-in and custom roles." },
    responses:  { heading: "Responses", body: "Aggregated submission data across all surveys in this project." },
    analytics:  { heading: "Analytics", body: "Charts and breakdowns for survey performance, completion rates, and answer distributions." },
    settings:   { heading: "Settings", body: "Project-level configuration: name, slug, visibility, integrations, and danger zone." },
    audit:      { heading: "Audit log", body: "A full history of changes made to this project and its surveys by all members." },
  };

  const NORMAL_TABS = ["overview", "surveys", "members", "roles"].map((id) => ({
    id,
    label: TAB_CONTENT[id].heading,
  }));

  const OVERFLOW_TABS = Object.keys(TAB_CONTENT).map((id) => ({
    id,
    label: TAB_CONTENT[id].heading,
  }));

  const [toggleStates, setToggleStates] = useState({
    toggle1: false,
    toggle2: true,
  });

  const [largeInputValues, setLargeInputValues] = useState({
    controlled: "",
    counted: "Initial summary text for the counted large input.",
    autoGrow:
      "Start typing here to test auto-grow.\n\nThis example begins with multiple lines so the resize behavior is visible immediately.",
  });

  const [selectValue, setSelectValue] = useState("option1");
  const [modalOpen, setModalOpen] = useState(false);

  const [stepperValues, setStepperValues] = useState({
    sm: 5,
    smSecondary: 5,
    smPill: 5,
    smSecondaryPill: 5,
    xs: 5,
    xsPill: 5,
    stepped: 10,
  });

  const [rangeGroups, setRangeGroups] = useState({
    sm: { min: 1, max: 2 },
    smSecondary: { min: 1, max: 2 },
    smPill: { min: 2, max: 6 },
    smSecondaryPill: { min: 2, max: 6 },
    smInput: { min: 2, max: 8 },
    xs: { min: 1, max: 2 },
    xsPill: { min: 3, max: 7 },
    stepped: { min: 10, max: 20 },
  });

  const handleToggle = (key: string, checked: boolean) => {
    setToggleStates((prev) => ({ ...prev, [key]: checked }));
  };

  const updateLargeInputValue = (
    key: keyof typeof largeInputValues,
    value: string,
  ) => {
    setLargeInputValues((current) => ({ ...current, [key]: value }));
  };

  const updateStepperValue = (key: keyof typeof stepperValues, value: number) => {
    setStepperValues((current) => ({ ...current, [key]: value }));
  };

  const updateRangeGroup = (
    groupKey: keyof typeof rangeGroups,
    itemKey: "min" | "max",
    value: number,
  ) => {
    setRangeGroups((current) => ({
      ...current,
      [groupKey]: {
        ...current[groupKey],
        [itemKey]: value,
      },
    }));
  };

  return (
    <div className="min-h-screen w-full bg-background px-4 py-5 text-foreground md:px-5 md:py-10">
      <div className="mx-auto max-w-1400px">
        <div className="mb-8 flex items-center justify-between gap-4 border-b-2 border-border pb-5 md:mb-10">
          <h1 className="m-0">UI Component Test Suite</h1>
          <ThemeToggle />
        </div>
        <Section title="Inputs">
          <TestGrid>
            <TestCard title="Text Input">
              <div className="flex-1" />

              {/* User menu */}
              <div className="mx-2">
                <Button
                  variant="ghost"
                  aria-expanded={false}
                  onClick={() => {}}
                  className="sidebar-nav-item flex w-full items-center gap-3 p-2 text-left"
                >
                  {/* Avatar */}
                  <span className="sidebar-nav-item__icon shrink-0">
                    <span className="flex h-8 w-8 items-center justify-center">
                      <span className="sidebar-avatar sidebar-avatar--user">
                        SM
                      </span>
                    </span>
                  </span>

                  {/* Name + email */}
                  <span className="sidebar-nav-item__label flex min-w-0 flex-1 flex-col items-start">
                    <span className="truncate text-sm font-semibold text-foreground">
                      Shayman McGee
                    </span>

                    <span className="truncate text-xs text-muted-foreground">
                      shayman@example.com
                    </span>
                  </span>

                  {/* Chevron */}
                  <span className="shrink-0 text-muted-foreground transition-transform duration-200">
                    
                  </span>
                </Button>
              </div>
            </TestCard>
          </TestGrid>
        </Section>


        <Section title="Survey member role variants">
          <CardStack gap="lg">
            <TestCard title="Variant A — Effective permissions first">
              <p className="mb-3 text-xs leading-5 text-muted-foreground">
                Lead with what the person can actually do. Roles are pushed to a "Source" column as the
                <em> how</em>, not the headline. Best when reviewers ask "what can this person do?"
              </p>
              <VariantEffectivePermissions />
            </TestCard>

            <TestCard title="Variant B — Additive naming (+ Grant)">
              <p className="mb-3 text-xs leading-5 text-muted-foreground">
                Survey grants are named after what they <em>add</em> ("+ Publish", "+ Manage"), not as a parallel
                hierarchy. Gained permissions are highlighted in the effective list. Makes the additive nature literal.
              </p>
              <VariantAdditiveNaming />
            </TestCard>

            <TestCard title="Variant C — Collapsed default case">
              <p className="mb-3 text-xs leading-5 text-muted-foreground">
                Members without an override show only their project role and a quiet summary line. Overridden rows
                get a left-border accent, an "Override" pill, and an explicit "Gains on this survey" block.
                Optimizes for the common case where most rows have no overrides.
              </p>
              <VariantCollapsedDefault />
            </TestCard>
          </CardStack>
        </Section>

        <Section title="Table">
          <CardStack gap="lg">
            <TestCard title="All columns visible">
              <Table
                columns={ALL_COLUMNS}
                rows={TABLE_ROWS}
                getRowKey={(row) => row.id}
              />
            </TestCard>

            <TestCard title="Version column hidden">
              <Table
                columns={HIDDEN_VERSION_COLUMNS}
                rows={TABLE_ROWS}
                getRowKey={(row) => row.id}
              />
            </TestCard>

            <TestCard title="Narrow container — scale-to-fit (max-w-xs)">
              <div className="max-w-xs">
                <Table
                  columns={ALL_COLUMNS}
                  rows={TABLE_ROWS}
                  getRowKey={(row) => row.id}
                />
              </div>
            </TestCard>

            <TestCard title="Striped rows">
              <Table
                columns={ALL_COLUMNS}
                rows={TABLE_ROWS}
                getRowKey={(row) => row.id}
                striped
              />
            </TestCard>

            <TestCard title="Striped + clickable">
              <Table
                columns={ALL_COLUMNS}
                rows={TABLE_ROWS}
                getRowKey={(row) => row.id}
                striped
                onRowClick={(row) => alert(`Clicked: ${row.name}`)}
              />
            </TestCard>

            <TestCard title="Clickable rows">
              <Table
                hideHeader={true}
                className=""
                columns={ALL_COLUMNS}
                rows={TABLE_ROWS}
                getRowKey={(row) => row.id}
                onRowClick={(row) => alert(`Clicked: ${row.name}`)}
              />
            </TestCard>

            <TestCard title="Empty state">
              <Table
                columns={ALL_COLUMNS}
                rows={[]}
                emptyState={<p className="text-sm text-muted-foreground">No surveys found.</p>}
              />
            </TestCard>
          </CardStack>
        </Section>

        <Section title="Tab Selector">
          <TestGrid>
            <TestCard title="4 Tabs">
              <TabSelector
                items={NORMAL_TABS}
                activeId={tabActive}
                onChange={setTabActive}
              />
              <div className="pt-4">
                <p className="text-sm font-semibold text-foreground">
                  {TAB_CONTENT[tabActive].heading}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {TAB_CONTENT[tabActive].body}
                </p>
              </div>
            </TestCard>

            <TestCard title="8 Tabs — overflow scroll">
              <TabSelector
                items={OVERFLOW_TABS}
                activeId={tabOverflowActive}
                onChange={setTabOverflowActive}
              />
              <div className="pt-4">
                <p className="text-sm font-semibold text-foreground">
                  {TAB_CONTENT[tabOverflowActive].heading}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {TAB_CONTENT[tabOverflowActive].body}
                </p>
              </div>
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Tabs (shadcn)">
          <TestGrid>
            <TestCard title="Default variant">
              <Tabs defaultValue="account">
                <TabsList>
                  <TabsTrigger value="account">Account</TabsTrigger>
                  <TabsTrigger value="password">Password</TabsTrigger>
                  <TabsTrigger value="notifications">Notifications</TabsTrigger>
                </TabsList>
                <TabsContent value="account">
                  <p className="text-sm text-muted-foreground">Manage your account settings and preferences.</p>
                </TabsContent>
                <TabsContent value="password">
                  <p className="text-sm text-muted-foreground">Change your password and security options.</p>
                </TabsContent>
                <TabsContent value="notifications">
                  <p className="text-sm text-muted-foreground">Configure how and when you receive notifications.</p>
                </TabsContent>
              </Tabs>
            </TestCard>

            <TestCard title="Line variant">
              <Tabs defaultValue="overview">
                <TabsList variant="line">
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="surveys">Surveys</TabsTrigger>
                  <TabsTrigger value="members">Members</TabsTrigger>
                </TabsList>
                <TabsContent value="overview">
                  <p className="text-sm text-muted-foreground">Project overview and key metrics.</p>
                </TabsContent>
                <TabsContent value="surveys">
                  <p className="text-sm text-muted-foreground">All surveys in this project.</p>
                </TabsContent>
                <TabsContent value="members">
                  <p className="text-sm text-muted-foreground">Team members with access to this project.</p>
                </TabsContent>
              </Tabs>
            </TestCard>

            <TestCard title="Vertical orientation">
              <Tabs defaultValue="general" orientation="vertical">
                <TabsList>
                  <TabsTrigger value="general">General</TabsTrigger>
                  <TabsTrigger value="integrations">Integrations</TabsTrigger>
                  <TabsTrigger value="danger">Danger zone</TabsTrigger>
                </TabsList>
                <TabsContent value="general">
                  <p className="text-sm text-muted-foreground">General project settings.</p>
                </TabsContent>
                <TabsContent value="integrations">
                  <p className="text-sm text-muted-foreground">Connect third-party integrations.</p>
                </TabsContent>
                <TabsContent value="danger">
                  <p className="text-sm text-muted-foreground">Irreversible and destructive actions.</p>
                </TabsContent>
              </Tabs>
            </TestCard>

            <TestCard title="Disabled tab">
              <Tabs defaultValue="active">
                <TabsList>
                  <TabsTrigger value="active">Active</TabsTrigger>
                  <TabsTrigger value="disabled" disabled>Disabled</TabsTrigger>
                  <TabsTrigger value="other">Other</TabsTrigger>
                </TabsList>
                <TabsContent value="active">
                  <p className="text-sm text-muted-foreground">This tab is active and selectable.</p>
                </TabsContent>
                <TabsContent value="other">
                  <p className="text-sm text-muted-foreground">Another selectable tab.</p>
                </TabsContent>
              </Tabs>
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Button Group">
          <TestGrid>
            <TestCard title="3 actions — fits">
              <ButtonGroup
                size="sm"
                items={[
                  { key: "edit",   label: "Edit",   onClick: () => {} },
                  { key: "share",  label: "Share",  onClick: () => {} },
                  { key: "delete", label: "Delete", variant: "danger", onClick: () => {} },
                ]}
              />
            </TestCard>

            <TestCard title="Overflow — narrow container">
              <div className="w-40">
                <ButtonGroup
                  size="sm"
                  items={[
                    { key: "edit",     label: "Edit",     onClick: () => {} },
                    { key: "preview",  label: "Preview",  onClick: () => {} },
                    { key: "share",    label: "Share",    onClick: () => {} },
                    { key: "archive",  label: "Archive",  onClick: () => {} },
                    { key: "delete",   label: "Delete",   variant: "danger", onClick: () => {} },
                  ]}
                />
              </div>
            </TestCard>

            <TestCard title="MD size">
              <ButtonGroup
                size="md"
                items={[
                  { key: "save",    label: "Save",    variant: "primary", onClick: () => {} },
                  { key: "discard", label: "Discard", onClick: () => {} },
                ]}
              />
            </TestCard>

            <TestCard title="XS size">
              <ButtonGroup
                size="xs"
                items={[
                  { key: "approve", label: "Approve", variant: "primary", onClick: () => {} },
                  { key: "reject",  label: "Reject",  variant: "danger",  onClick: () => {} },
                  { key: "defer",   label: "Defer",   onClick: () => {} },
                ]}
              />
            </TestCard>

            <TestCard title="With disabled item">
              <ButtonGroup
                size="sm"
                items={[
                  { key: "publish",  label: "Publish",  variant: "primary", onClick: () => {} },
                  { key: "schedule", label: "Schedule", disabled: true,     onClick: () => {} },
                  { key: "delete",   label: "Delete",   variant: "danger",  onClick: () => {} },
                ]}
              />
            </TestCard>

            <TestCard title="Single action">
              <ButtonGroup
                size="sm"
                items={[
                  { key: "export", label: "Export CSV", onClick: () => {} },
                ]}
              />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Buttons">
          <TestGrid>
            {buttonVariants.map((variant) => (
              <TestCard
                key={`${variant}-standard`}
                title={`${buttonVariantLabels[variant]} / Standard`}
              >
                <InlineStack>
                  {buttonSizes.map((size) => (
                    <Button key={`${variant}-${size}`} variant={variant} size={size}>
                      {buttonSizeLabels[size]}
                    </Button>
                  ))}
                </InlineStack>
              </TestCard>
            ))}

            {buttonVariants.map((variant) => (
              <TestCard
                key={`${variant}-pill`}
                title={`${buttonVariantLabels[variant]} / Pill`}
              >
                <InlineStack>
                  {buttonSizes.map((size) => (
                    <Button key={`${variant}-${size}-pill`} variant={variant} size={size} pill>
                      {buttonSizeLabels[size]}
                    </Button>
                  ))}
                </InlineStack>
              </TestCard>
            ))}

            {buttonVariants.map((variant) => (
              <TestCard
                key={`${variant}-disabled`}
                title={`${buttonVariantLabels[variant]} / Disabled`}
              >
                <InlineStack>
                  {buttonSizes.map((size) => (
                    <Button
                      key={`${variant}-${size}-disabled`}
                      variant={variant}
                      size={size}
                      disabled
                    >
                      {buttonSizeLabels[size]}
                    </Button>
                  ))}
                </InlineStack>
              </TestCard>
            ))}

            {buttonVariants.map((variant) => (
              <TestCard
                key={`${variant}-dotted`}
                title={`${buttonVariantLabels[variant]} / Dotted Border`}
              >
                <InlineStack>
                  {buttonSizes.map((size) => (
                    <Button
                      key={`${variant}-${size}-dotted`}
                      variant={variant}
                      size={size}
                      borderStyle="dotted"
                    >
                      {buttonSizeLabels[size]}
                    </Button>
                  ))}
                </InlineStack>
              </TestCard>
            ))}

            {buttonVariants.map((variant) => (
              <TestCard
                key={`${variant}-icon`}
                title={`${buttonVariantLabels[variant]} / Icon (plus)`}
              >
                <InlineStack>
                  {buttonSizes.map((size) => (
                    <Button
                      key={`${variant}-${size}-icon`}
                      variant={variant}
                      size={size}
                      icon="plus"
                    >
                      {buttonSizeLabels[size]}
                    </Button>
                  ))}
                </InlineStack>
              </TestCard>
            ))}
          </TestGrid>
        </Section>

        <Section title="Tooltip">
          <TestGrid>
            <TestCard title="Ghost Button Sizes">
              <WideStack>
                <Tooltip title="Delete" size="sm">
                  <Button variant="ghost">Small</Button>
                </Tooltip>

                <Tooltip title="Delete" size="md">
                  <Button variant="ghost">Medium</Button>
                </Tooltip>

                <Tooltip title="Delete" size="lg">
                  <Button variant="ghost">Large</Button>
                </Tooltip>
              </WideStack>
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Large Input">
          <TestGrid>
            <TestCard title="Size SM / Placeholder">
              <LargeInput
                label="Quick Note"
                size="sm"
                placeholder="Write a short note..."
                hint="Tests size, label, placeholder, and name"
                name="quickNote"
              />
            </TestCard>

            <TestCard title="Size MD / Rows">
              <LargeInput
                label="Description"
                size="md"
                rows={5}
                defaultValue="Medium large-input variant with a little more room for longer messages."
                placeholder="Add a medium-length description..."
                hint="Tests default value and rows"
              />
            </TestCard>

            <TestCard title="Size LG / Placeholder">
              <LargeInput
                label="Detailed Summary"
                size="lg"
                placeholder="Write a detailed summary..."
                hint="Expanded large-input size"
                required
                autoComplete="off"
              />
            </TestCard>

            <TestCard title="Controlled Value">
              <LargeInput
                label="Controlled Notes"
                size="md"
                value={largeInputValues.controlled}
                onChange={(event) =>
                  updateLargeInputValue("controlled", event.target.value)
                }
                placeholder="Type to test value and onChange..."
                hint="Tests controlled textarea behavior"
              />
            </TestCard>

            <TestCard title="Character Count">
              <LargeInput
                label="Summary"
                size="md"
                value={largeInputValues.counted}
                onChange={(event) =>
                  updateLargeInputValue("counted", event.target.value)
                }
                placeholder="Write a concise summary..."
                hint="Tests maxText and showCount"
                maxText={180}
                showCount
              />
            </TestCard>

            <TestCard title="Auto Grow">
              <LargeInput
                label="Auto-Growing Notes"
                size="sm"
                value={largeInputValues.autoGrow}
                onChange={(event) =>
                  updateLargeInputValue("autoGrow", event.target.value)
                }
                placeholder="Type multiple lines to grow the field..."
                hint="Tests autoGrow and maxAutoGrowHeight"
                autoGrow
                maxAutoGrowHeight={220}
              />
            </TestCard>

            <TestCard title="Error State">
              <LargeInput
                label="Feedback"
                size="md"
                placeholder="Explain what went wrong..."
                error="Feedback is required before continuing."
              />
            </TestCard>

            <TestCard title="Disabled">
              <LargeInput
                label="Archived Notes"
                size="sm"
                defaultValue="This field is disabled."
                placeholder="Disabled input"
                disabled
                hint="Disabled textarea state"
              />
            </TestCard>

            <TestCard title="Read Only">
              <LargeInput
                label="Reference Copy"
                size="sm"
                defaultValue="This content is read-only but still selectable."
                placeholder="Read-only input"
                readOnly
                hint="Tests readOnly behavior"
              />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Number Up/Down">
          <TestGrid>
            <TestCard title="Size SM Primary">
              <NumberStepper
                value={stepperValues.sm}
                onChange={(value) => updateStepperValue("sm", value)}
                min={1}
                max={10}
                step={1}
                size="sm"
                variant="primary"
              />
            </TestCard>

            <TestCard title="Size SM Primary Pill">
              <NumberStepper
                value={stepperValues.smPill}
                onChange={(value) => updateStepperValue("smPill", value)}
                min={1}
                max={10}
                step={1}
                size="sm"
                variant="primary"
                pill
              />
            </TestCard>

            <TestCard title="Size SM Secondary">
              <NumberStepper
                value={stepperValues.smSecondary}
                onChange={(value) => updateStepperValue("smSecondary", value)}
                min={1}
                max={10}
                step={1}
                size="sm"
                variant="secondary"
              />
            </TestCard>

            <TestCard title="Size SM Secondary Pill">
              <NumberStepper
                value={stepperValues.smSecondaryPill}
                onChange={(value) => updateStepperValue("smSecondaryPill", value)}
                min={1}
                max={10}
                step={1}
                size="sm"
                pill
                variant="secondary"
              />
            </TestCard>

            <TestCard title="Size XS Ghost">
              <NumberStepper
                value={stepperValues.xs}
                onChange={(value) => updateStepperValue("xs", value)}
                min={1}
                max={10}
                step={1}
                size="xs"
                variant="ghost"
              />
            </TestCard>

            <TestCard title="Size XS Ghost Pill">
              <NumberStepper
                value={stepperValues.xsPill}
                onChange={(value) => updateStepperValue("xsPill", value)}
                min={1}
                max={10}
                step={1}
                size="xs"
                variant="ghost"
                pill
              />
            </TestCard>

            <TestCard title="Range 0-100, Step 5">
              <NumberStepper
                value={stepperValues.stepped}
                onChange={(value) => updateStepperValue("stepped", value)}
                min={0}
                max={100}
                step={5}
              />
            </TestCard>

            <TestCard title="Disabled">
              <NumberStepper value={5} onChange={() => {}} disabled />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Number Stepper Group">
          <TestGrid>
            <TestCard title="Size SM Primary">
              <NumberStepperGroup
                size="sm"
                variant="primary"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.sm.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.sm.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) => updateRangeGroup("sm", key as "min" | "max", value)}
              />
            </TestCard>

            <TestCard title="Size SM Primary Pill">
              <NumberStepperGroup
                size="sm"
                variant="primary"
                pill
                items={[
                  { key: "min", label: "Min", value: rangeGroups.smPill.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.smPill.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) => updateRangeGroup("smPill", key as "min" | "max", value)}
              />
            </TestCard>

            <TestCard title="Size SM Secondary">
              <NumberStepperGroup
                size="sm"
                variant="secondary"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.smSecondary.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.smSecondary.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) =>
                  updateRangeGroup("smSecondary", key as "min" | "max", value)
                }
              />
            </TestCard>

            <TestCard title="Size SM Secondary Pill">
              <NumberStepperGroup
                size="sm"
                pill
                variant="secondary"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.smSecondaryPill.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.smSecondaryPill.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) =>
                  updateRangeGroup("smSecondaryPill", key as "min" | "max", value)
                }
              />
            </TestCard>

            <TestCard title="Size SM Secondary Input">
              <NumberStepperGroup
                size="sm"
                variant="secondary"
                allowInput
                items={[
                  { key: "min", label: "Min", value: rangeGroups.smInput.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.smInput.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) =>
                  updateRangeGroup("smInput", key as "min" | "max", value)
                }
              />
            </TestCard>

            <TestCard title="Size XS Ghost">
              <NumberStepperGroup
                size="xs"
                variant="ghost"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.xs.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.xs.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) => updateRangeGroup("xs", key as "min" | "max", value)}
              />
            </TestCard>

            <TestCard title="Size XS Ghost Pill">
              <NumberStepperGroup
                size="xs"
                variant="ghost"
                pill
                items={[
                  { key: "min", label: "Min", value: rangeGroups.xsPill.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.xsPill.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) => updateRangeGroup("xsPill", key as "min" | "max", value)}
              />
            </TestCard>

            <TestCard title="Step 5 / Wide Range">
              <NumberStepperGroup
                size="sm"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.stepped.min, min: 0, max: 50, step: 5 },
                  { key: "max", label: "Max", value: rangeGroups.stepped.max, min: 0, max: 50, step: 5 },
                ]}
                onChange={(key, value) =>
                  updateRangeGroup("stepped", key as "min" | "max", value)
                }
              />
            </TestCard>

            <TestCard title="Disabled">
              <NumberStepperGroup
                size="sm"
                items={[
                  { key: "min", label: "Min", value: 2, min: 0, max: 10, disabled: true },
                  { key: "max", label: "Max", value: 6, min: 0, max: 10, disabled: true },
                ]}
                onChange={() => {}}
              />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Badges">
          <TestGrid>
            <TestCard title="Default">
              <Badge>Default Badge</Badge>
            </TestCard>
            <TestCard title="Success">
              <Badge variant="success">Success Badge</Badge>
            </TestCard>
            <TestCard title="Danger">
              <Badge variant="danger">Danger Badge</Badge>
            </TestCard>
            <TestCard title="Warning">
              <Badge variant="warning">Warning Badge</Badge>
            </TestCard>
            <TestCard title="Accent">
              <Badge variant="accent">Accent Badge</Badge>
            </TestCard>
            <TestCard title="Muted">
              <Badge variant="muted">Muted Badge</Badge>
            </TestCard>
            <TestCard title="Sizes">
              <WideStack>
                <Badge size="sm">Small</Badge>
                <Badge size="md">Medium</Badge>
                <Badge size="lg">Large</Badge>
                <Badge size="xl">Extra Large</Badge>
              </WideStack>
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Inputs">
          <TestGrid>
            <TestCard title="Default">
              <Input label="Name" placeholder="Default" />
            </TestCard>
            <TestCard title="Small">
              <Input label="Compact" size="sm" placeholder="Smaller input" />
            </TestCard>
            <TestCard title="Ghost">
              <Input label="Ghost" variant="ghost" placeholder="Ghost input" />
            </TestCard>
            <TestCard title="Quiet">
              <Input label="Quiet" variant="quiet" placeholder="Quiet input" />
            </TestCard>
            <TestCard title="Pill">
              <Input label="Pill" variant="secondary" pill placeholder="Pill input" />
            </TestCard>
            <TestCard title="Disabled">
              <Input label="Disabled" variant="quiet" disabled value="Disabled value" />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Select Dropdown">
          <TestGrid>
            <TestCard>
              <Select
                label="Choose an option"
                options={[
                  { value: "option1", label: "Option 1" },
                  { value: "option2", label: "Option 2" },
                  { value: "option3", label: "Option 3" },
                ]}
                value={selectValue}
                onChange={(e) => setSelectValue(e.target.value)}
              />
            </TestCard>
            <TestCard>
              <Select
                label="With Hint"
                options={[
                  { value: "yes", label: "Yes" },
                  { value: "no", label: "No" },
                  { value: "maybe", label: "Maybe" },
                ]}
                hint="Select one of the options above"
              />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Toggles">
          <TestGrid>
            <TestCard>
              <Toggle
                label="Enable notifications"
                checked={toggleStates.toggle1}
                onChange={(checked) => handleToggle("toggle1", checked)}
              />
            </TestCard>
            <TestCard>
              <Toggle
                label="Dark mode (enabled)"
                checked={toggleStates.toggle2}
                onChange={(checked) => handleToggle("toggle2", checked)}
              />
            </TestCard>
            <TestCard>
              <Toggle label="Disabled toggle" checked={false} onChange={() => {}} disabled />
            </TestCard>
            <TestCard>
              <Toggle
                label="With hint text"
                checked={toggleStates.toggle1}
                onChange={(checked) => handleToggle("toggle1", checked)}
                hint="This toggle has a helpful hint below"
              />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Spinners">
          <TestGrid>
            <TestCard title="Small (16px)">
              <Spinner size={16} />
            </TestCard>
            <TestCard title="Medium (24px)">
              <Spinner size={24} />
            </TestCard>
            <TestCard title="Large (32px)">
              <Spinner size={32} />
            </TestCard>
            <TestCard title="Extra Large (48px)">
              <Spinner size={48} />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Modal">
          <TestGrid>
            <TestCard>
              <Button variant="primary" onClick={() => setModalOpen(true)}>
                Open Modal
              </Button>
            </TestCard>
          </TestGrid>
        </Section>

        <Modal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          title="Test Modal"
          footer={
            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={() => setModalOpen(false)}>
                Confirm
              </Button>
            </div>
          }
        >
          <div className="flex flex-col gap-4">
            <p>
              This is a test modal dialog. You can interact with all the UI components inside it.
            </p>
            <Input label="Modal Input" placeholder="Type something..." />
            <Select
              label="Modal Select"
              options={[
                { value: "opt1", label: "Option 1" },
                { value: "opt2", label: "Option 2" },
              ]}
            />
          </div>
        </Modal>
      </div>
    </div>
  );
}
