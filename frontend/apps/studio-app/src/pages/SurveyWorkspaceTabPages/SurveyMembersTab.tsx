import { useMemo, useRef, useState, type MouseEventHandler, type ReactNode } from 'react'
import { Badge, Button, DropdownMenu, Modal, PermissionTag, Select, Table, type TableColumn } from '@flowform/ui'
import { KeyRound, Shield, Trash2, UserCog } from 'lucide-react'
import {
  mockProjectMembers,
  mockSurveyMembers,
  type MockProjectMember,
  type MockSurveyMember,
} from '@/api/mockData'

type SurveyRole = MockSurveyMember['role']
type ProjectRole = MockProjectMember['role']

type SurveyAccessRow = MockProjectMember & {
  access: boolean
  effectiveSurveyRole: SurveyRole
  surveyRole?: SurveyRole
}

const PROJECT_ROLE_TO_SURVEY_ROLE: Record<ProjectRole, SurveyRole> = {
  Owner: 'Manager',
  Editor: 'Editor',
  Viewer: 'Viewer',
}

const ROLE_BADGE_VARIANT: Record<SurveyRole, 'accent' | 'warning' | 'muted' | 'default'> = {
  Manager: 'accent',
  Publisher: 'warning',
  Editor: 'default',
  Viewer: 'muted',
}

const PROJECT_ROLE_BADGE_VARIANT: Record<ProjectRole, 'accent' | 'default' | 'muted'> = {
  Owner: 'accent',
  Editor: 'default',
  Viewer: 'muted',
}

const SURVEY_ROLE_PERMISSIONS: Record<SurveyRole, string[]> = {
  Manager: ['Manage survey', 'Publish', 'Edit', 'View responses'],
  Publisher: ['Publish', 'Edit', 'View responses'],
  Editor: ['Edit', 'Preview'],
  Viewer: ['View'],
}

const PERMISSION_TOOLTIPS: Record<string, string> = {
  'Manage survey': 'Can manage survey settings, member access, and administrative survey actions.',
  Publish: 'Can publish survey drafts and update what respondents can access.',
  Edit: 'Can change survey questions, structure, and draft content.',
  'View responses': 'Can view collected survey responses and response summaries.',
  Preview: 'Can preview draft survey content before it is published.',
  View: 'Can view the survey setup and available survey details.',
}

const SURVEY_ROLES: SurveyRole[] = ['Manager', 'Publisher', 'Editor', 'Viewer']

function ActionButton({
  children,
  icon,
  variant = 'ghost',
  onClick,
}: {
  children: ReactNode
  icon: ReactNode
  variant?: 'ghost' | 'destructive'
  onClick?: MouseEventHandler<HTMLButtonElement>
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
  )
}

function SurveyAccessActions({
  member,
  onChangeRole,
  onRemoveSurveyRole,
}: {
  member: SurveyAccessRow
  onChangeRole: () => void
  onRemoveSurveyRole: (memberId: number) => void
}) {
  const triggerRef = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
  const iconProps = { size: 15, strokeWidth: 2 }

  const sections = [
    {
      actions: [
        {
          key: 'member',
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
          key: 'change-role',
          content: (
            <ActionButton icon={<UserCog {...iconProps} />}>
              Change role
            </ActionButton>
          ),
          onSelect: onChangeRole,
        },
        {
          key: 'remove-survey-role',
          content: (
            <ActionButton variant="destructive" icon={<Trash2 {...iconProps} />}>
              Remove role
            </ActionButton>
          ),
          onSelect: () => onRemoveSurveyRole(member.id),
        },
      ],
    },
  ]

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
        aria-label={`Survey access actions for ${member.name}`}
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
  )
}

export function SurveyMembersTab() {
  const [roleChange, setRoleChange] = useState<{ member: SurveyAccessRow; role: SurveyRole } | null>(null)
  const [surveyRoles, setSurveyRoles] = useState<Record<number, SurveyRole>>(() =>
    mockSurveyMembers.reduce<Record<number, SurveyRole>>((roles, member) => {
      if (!member.inherited) roles[member.id] = member.role
      return roles
    }, {}),
  )

  const rows = useMemo<SurveyAccessRow[]>(
    () =>
      mockProjectMembers.map((member) => {
        const surveyRole = surveyRoles[member.id]
        const effectiveSurveyRole = surveyRole ?? PROJECT_ROLE_TO_SURVEY_ROLE[member.role]
        return {
          ...member,
          access: true,
          effectiveSurveyRole,
          surveyRole,
        }
      }),
    [surveyRoles],
  )

  const setSurveyRole = (memberId: number, role: SurveyRole) => {
    setSurveyRoles((current) => ({ ...current, [memberId]: role }))
  }

  const openRoleChange = (member: SurveyAccessRow) => {
    setRoleChange({ member, role: member.surveyRole ?? member.effectiveSurveyRole })
  }

  const saveRoleChange = () => {
    if (!roleChange) return
    setSurveyRole(roleChange.member.id, roleChange.role)
    setRoleChange(null)
  }

  const removeSurveyRole = (memberId: number) => {
    setSurveyRoles((current) => {
      const next = { ...current }
      delete next[memberId]
      return next
    })
  }

  const columns: TableColumn<SurveyAccessRow>[] = [
    {
      key: 'access-indicator',
      header: <span className="sr-only">Survey access</span>,
      minWidth: 40,
      width: 40,
      cellClassName: 'flex justify-center p-0 pl-1',
      headerClassName: 'p-0',
      cell: (member) => (
        <span
          className={`size-2.5 rounded-full ${member.access ? 'bg-success' : 'bg-muted-foreground/40'}`}
          aria-label={member.access ? 'Can access survey' : 'Cannot access survey'}
        />
      ),
    },
    {
      key: 'member',
      header: 'Member',
      headerClassName: 'pl-0',
      cellClassName: 'pl-0',
      minWidth: 150,
      width: 200,
      cell: (member) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">{member.name}</p>
          <p className="truncate text-xs text-muted-foreground">{member.email}</p>
        </div>
      ),
    },
    {
      key: 'project-role',
      header: 'Project role',
      minWidth: 120,
      width: 130,
      cellClassName: 'flex justify-center',
      cell: (member) => (
        <Badge variant={PROJECT_ROLE_BADGE_VARIANT[member.role]} size="xs">
          {member.role}
        </Badge>
      ),
    },
    {
      key: 'survey-role',
      header: 'Survey role',
      minWidth: 120,
      width: 130,
      cellClassName: 'flex justify-center',
      cell: (member) => (
        <div className="flex items-center gap-2">
          <Badge variant={ROLE_BADGE_VARIANT[member.effectiveSurveyRole]} size="xs">
            {member.effectiveSurveyRole}
          </Badge>
        </div>
      ),
    },
    {
      key: 'permissions',
      header: 'Permissions',
      minWidth: 260,
      cell: (member) => (
        <div className="flex flex-wrap gap-1.5">
          {SURVEY_ROLE_PERMISSIONS[member.effectiveSurveyRole].map((permission) => (
            <PermissionTag
              key={permission}
              label={permission}
              tooltip={PERMISSION_TOOLTIPS[permission] ?? permission}
            />
          ))}
        </div>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      minWidth: 70,
      width: 80,
      cellClassName: 'flex justify-center px-2',
      headerClassName: 'justify-end text-right pl-2',
      cell: (member) => (
        <SurveyAccessActions
          member={member}
          onChangeRole={() => openRoleChange(member)}
          onRemoveSurveyRole={removeSurveyRole}
        />
      ),
    },
  ]

  return (
    <section className="grid gap-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Survey members</h2>
          <p className="text-sm text-muted-foreground">
            Review project members, their survey access, and survey-specific role overrides.
          </p>
        </div>
        <Button variant="primary" size="sm" icon="plus">
          Add member
        </Button>
      </div>

      <Table
        columns={columns}
        rows={rows}
        getRowKey={(member) => member.id}
      />

      <div className="grid gap-2 rounded-sm border border-border bg-muted/20 p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Shield size={16} aria-hidden="true" />
          Project and survey roles both apply
        </div>
        <p className="text-xs leading-5 text-muted-foreground">
          Project roles provide baseline survey access. Survey roles can override access for this survey without changing
          the member's project role.
        </p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <KeyRound size={14} aria-hidden="true" />
          Removing a survey role returns the member to their project-role permissions.
        </div>
      </div>

      <Modal
        open={Boolean(roleChange)}
        onClose={() => setRoleChange(null)}
        title="Change survey role"
        width={420}
        footer={(
          <>
            <Button variant="secondary" onClick={() => setRoleChange(null)} className="mr-auto">Cancel</Button>
            <Button variant="primary" onClick={saveRoleChange}>Save</Button>
          </>
        )}
      >
        {roleChange && (
          <div className="grid gap-4">
            <p className="text-sm leading-6 text-foreground">
              Select a survey role for {roleChange.member.name}.
            </p>
            <Select
              label="Survey role"
              value={roleChange.role}
              onChange={(event) => setRoleChange((current) =>
                current ? { ...current, role: event.target.value as SurveyRole } : current,
              )}
              options={SURVEY_ROLES.map((role) => ({ value: role, label: role }))}
            />
          </div>
        )}
      </Modal>
    </section>
  )
}
