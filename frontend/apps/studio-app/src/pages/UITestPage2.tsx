import { useRef, useState, type MouseEventHandler, type ReactNode } from "react";
import { Badge, Button, DropdownMenu, Table, type TableColumn } from "@flowform/ui";
import { useRenderDebug } from "@/debug/useRenderDebug";
import { mockProjectMembers, type MockProjectMember } from "@/api/mockData";
import { Trash2, UserCog } from "lucide-react";

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

const ADDITIVE_GRANT_LABEL: Record<SurveyRole, string> = {
  Manager: "+ Manage",
  Publisher: "+ Publish",
  Editor: "+ Edit",
  Viewer: "",
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

function ActionButton({
  children,
  icon,
  variant = "ghost",
  onClick,
}: {
  children: ReactNode;
  icon: ReactNode;
  variant?: "ghost" | "destructive";
  onClick?: MouseEventHandler<HTMLButtonElement>;
}) {
  return (
    <Button
      type="button"
      variant={variant}
      size="sm"
      onClick={onClick}
      className="mx-2 my-0.5 flex w-[calc(100%-1rem)] items-center justify-start gap-2"
    >
      <span className="inline-flex h-[15px] w-[15px] shrink-0 items-center justify-center">
        {icon}
      </span>
      <span>{children}</span>
    </Button>
  );
}

function MemberActions({ member }: { member: MemberRow }) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const iconProps = { size: 15, strokeWidth: 2 };

  const sections = [
    {
      actions: [
        {
          key: "member",
          closeOnSelect: false,
          content: (
            <div className="flex w-full min-w-0 flex-col gap-1 rounded-sm px-3 py-2">
              <span className="truncate text-sm font-semibold text-foreground">{member.name}</span>
              <span className="truncate text-xs text-muted-foreground">{member.email}</span>
            </div>
          ),
        },
      ],
    },
    {
      actions: [
        {
          key: "change-role",
          content: (
            <ActionButton icon={<UserCog {...iconProps} />}>
              Change role
            </ActionButton>
          ),
        },
        {
          key: "remove-survey-role",
          content: (
            <ActionButton variant="destructive" icon={<Trash2 {...iconProps} />}>
              Remove role
            </ActionButton>
          ),
        },
      ],
    },
  ];

  return (
    <>
      <Button
        ref={triggerRef}
        type="button"
        variant="icon"
        size="xs"
        icon="ellipsis"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Member actions for ${member.name}`}
        onClick={() => setOpen((o) => !o)}
      />
      <DropdownMenu
        open={open}
        onClose={() => setOpen(false)}
        trigger={triggerRef}
        width="14rem"
        align="right"
        direction="auto"
        fullscreenAt="never"
        sections={sections}
      />
    </>
  );
}

export function UITestPage2() {
  useRenderDebug("UITestPage2");

  const rows = buildMemberRows();

  const columns: TableColumn<MemberRow>[] = [
    {
      key: "member",
      header: "Member",
      minWidth: 100,
      maxWidth: 200,
      cell: (m) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">{m.name}</p>
          <p className="truncate text-2xs text-muted-foreground">{m.email}</p>
        </div>
      ),
    },
    {
      key: "project-role",
      header: "Project role",
      minWidth: 65,
      maxWidth: 150,
      cell: (m) => (
        <Badge variant="default" size="xs">
          {m.role}
        </Badge>
      ),
    },
    {
      key: "survey-role",
      header: "Survey role",
      minWidth: 75,
      maxWidth: 150,
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
      minWidth: 110,
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
    {
      key: "actions",
      header: <span className="sr-only">Actions</span>,
      minWidth: 50,
      maxWidth: 50,
      headerClassName: "flex justify-center text-right pr-2",
      cellClassName: "flex justify-center px-0",
      cell: (member) => <MemberActions member={member} />,
    },
  ];

  return (
    <main className="page-main">
      <h1>UI Test 2</h1>
      <p className="mt-2 mb-6 text-sm text-muted-foreground">
        Variant B — additive naming. Project roles and inherited permissions use the default variant;
        survey grants and override-gained permissions use warning.
      </p>
      <div className="max-w-250">
        <Table columns={columns} rows={rows} getRowKey={(m) => m.id} />
      </div>
    </main>
  );
}
