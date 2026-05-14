import { useCallback, useMemo, useRef, useState } from 'react'
import { Button, Badge, DropdownMenu, Input, Modal, Select, Table, type TableColumn } from '@flowform/ui'
import { mockProjectMembers, type MockProjectMember } from '@/api/mockData'
import { PERMISSION_GROUPS, PRESET_ROLES, type CustomRole } from './RolesTab'
import { RoleEditorModal, type RoleEditorState } from './RoleEditorModal'

const actionIconProps = {
  width: 15,
  height: 15,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
}

function IconUserCog() {
  return (
    <svg {...actionIconProps}>
      <circle cx="9" cy="7" r="4" />
      <path d="M3 21v-2a4 4 0 0 1 4-4h4" />
      <circle cx="18" cy="17" r="2.5" />
      <path d="M18 13.5v1M18 19.5v1M14.5 17h1M20.5 17h1" />
    </svg>
  )
}

function IconTrash() {
  return (
    <svg {...actionIconProps}>
      <path d="M3 6h18" />
      <path d="M8 6V4h8v2" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v5" />
      <path d="M14 11v5" />
    </svg>
  )
}

function MemberActionsMenu({
  member,
  onChangeRole,
  onRemove,
}: {
  member: MockProjectMember
  onChangeRole: () => void
  onRemove: () => void
}) {
  const triggerRef = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)

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
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mx-2 my-0.5 flex w-[calc(100%-1rem)] items-center justify-start gap-2"
            >
              <span className="inline-flex h-[15px] w-[15px] shrink-0 items-center justify-center">
                <IconUserCog />
              </span>
              <span>Change role</span>
            </Button>
          ),
          onSelect: onChangeRole,
        },
        {
          key: 'remove',
          content: (
            <Button
              type="button"
              variant="destructive"
              size="sm"
              className="mx-2 my-0.5 flex w-[calc(100%-1rem)] items-center justify-start gap-2"
            >
              <span className="inline-flex h-[15px] w-[15px] shrink-0 items-center justify-center">
                <IconTrash />
              </span>
              <span>Remove</span>
            </Button>
          ),
          onSelect: onRemove,
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
        aria-label={`Actions for ${member.name}`}
        onClick={() => setOpen((o) => !o)}
      />
      <DropdownMenu
        open={open}
        onClose={() => setOpen(false)}
        trigger={triggerRef}
        sections={sections}
        size="md"
        align="right"
        direction="auto"
        fullscreenAt="never"
      />
    </>
  )
}

export function MembersTab() {
  const [members, setMembers] = useState<MockProjectMember[]>(mockProjectMembers)
  const [memberToRemove, setMemberToRemove] = useState<MockProjectMember | null>(null)
  const [roleChange, setRoleChange] = useState<{ member: MockProjectMember; roleId: string } | null>(null)

  // ── Invite modal ────────────────────────────────────────────────────────────
  const [inviteOpen, setInviteOpen] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newRoleId, setNewRoleId] = useState(PRESET_ROLES[2].id) // default: analyst

  // ── Role editor modal (nested) ──────────────────────────────────────────────
  const [customRoles, setCustomRoles] = useState<CustomRole[]>([])
  const [editingRole, setEditingRole] = useState<RoleEditorState | null>(null)

  const allRoles = useMemo(() => [
    ...PRESET_ROLES,
    ...customRoles,
  ], [customRoles])

  const addCustomRole = () => {
    const id = `custom-${Date.now()}`
    setEditingRole({ id, custom: true, name: 'New role', description: 'Custom project role.', permissions: new Set() })
    setInviteOpen(false)
  }

  const saveRole = () => {
    if (!editingRole) return
    const next = {
      name: editingRole.name.trim(),
      description: editingRole.description.trim(),
      permissions: [...editingRole.permissions],
    }
    if (!next.name) return
    setCustomRoles((c) =>
      c.some((r) => r.id === editingRole.id)
        ? c.map((r) => r.id === editingRole.id ? { ...r, ...next } : r)
        : [...c, { id: editingRole.id, ...next }],
    )
    setNewRoleId(editingRole.id)
    setEditingRole(null)
    setInviteOpen(true)
  }

  const deleteRole = () => {
    if (!editingRole?.custom) return
    setCustomRoles((c) => c.filter((r) => r.id !== editingRole.id))
    if (newRoleId === editingRole.id) setNewRoleId(PRESET_ROLES[2].id)
    setEditingRole(null)
  }

  // ── Invite submit ───────────────────────────────────────────────────────────
  const sendInvite = () => {
    const email = newEmail.trim()
    if (!email) return
    const name = email.split('@')[0].replace(/[._-]+/g, ' ')
    const role = allRoles.find((r) => r.id === newRoleId)
    setMembers((c) => [
      ...c,
      {
        id: Date.now(),
        name: name.replace(/\b\w/g, (l) => l.toUpperCase()),
        email,
        role: (role?.name ?? 'Viewer') as MockProjectMember['role'],
        status: 'Invited',
      },
    ])
    setNewEmail('')
    setInviteOpen(false)
  }

  const removeMember = () => {
    if (!memberToRemove) return
    setMembers((c) => c.filter((m) => m.id !== memberToRemove.id))
    setMemberToRemove(null)
  }

  const openRoleChange = useCallback((member: MockProjectMember) => {
    const roleId = allRoles.find((role) => role.name === member.role)?.id ?? PRESET_ROLES[2].id
    setRoleChange({ member, roleId })
  }, [allRoles])

  const saveRoleChange = () => {
    if (!roleChange) return
    const role = allRoles.find((r) => r.id === roleChange.roleId)
    if (!role) return
    setMembers((c) =>
      c.map((member) =>
        member.id === roleChange.member.id
          ? { ...member, role: role.name as MockProjectMember['role'] }
          : member,
      ),
    )
    setRoleChange(null)
  }

  // ── Table columns ───────────────────────────────────────────────────────────
  const memberColumns = useMemo<TableColumn<MockProjectMember>[]>(() => [
    {
      key: 'member',
      header: 'Member',
      minWidth: 200,
      cell: (row) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">{row.name}</p>
          <p className="truncate text-xs text-muted-foreground">{row.email}</p>
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      minWidth: 100,
      cell: (row) => <Badge variant="muted" size="xs">{row.role}</Badge>,
    },
    {
      key: 'status',
      header: 'Status',
      minWidth: 100,
      cell: (row) => (
        <Badge variant={row.status === 'Active' ? 'success' : 'warning'} size="xs">
          {row.status}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      minWidth: 50,
      cellClassName: 'flex justify-end',
      cell: (row) => (
        <MemberActionsMenu
          member={row}
          onChangeRole={() => openRoleChange(row)}
          onRemove={() => setMemberToRemove(row)}
        />
      ),
    },
  ], [openRoleChange])

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <section className="grid max-w-6xl gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Members</h2>
          <p className="text-sm text-muted-foreground">{members.length} total</p>
        </div>
        <Button variant="primary" size="sm" icon="plus" onClick={() => setInviteOpen(true)}>
          Invite member
        </Button>
      </div>

      <Table
        columns={memberColumns}
        rows={members}
        getRowKey={(row) => row.id}
      />

      {/* ── Invite modal ─────────────────────────────────────────────────────── */}
      <Modal
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        title="Invite member"
        width={780}
        footer={(
          <>
            <Button variant="secondary" onClick={() => setInviteOpen(false)}>Cancel</Button>
            <Button variant="primary" onClick={sendInvite} disabled={!newEmail.trim()}>
              Send invite
            </Button>
          </>
        )}
      >
        <div className="grid gap-4">
          <Input
            label="Email address"
            type="email"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            placeholder="name@example.com"
          />
          <div className="flex items-end gap-2">
            <div className="flex-0">
              <Select
                label="Role"
                value={newRoleId}
                className='w-50'
                onChange={(e) => setNewRoleId(e.target.value)}
                options={allRoles.map((r) => ({ value: r.id, label: r.name }))}
              />
            </div>
            <Button variant="secondary" size="md" onClick={addCustomRole}>
              New role
            </Button>
          </div>
        </div>
      </Modal>

      <RoleEditorModal
        role={editingRole}
        onClose={() => { setEditingRole(null); setInviteOpen(true); }}
        onChange={setEditingRole}
        onSave={saveRole}
        onDelete={deleteRole}
        permissionGroups={PERMISSION_GROUPS}
        isNew
      />

      <Modal
        open={Boolean(memberToRemove)}
        onClose={() => setMemberToRemove(null)}
        title="Remove member"
        width={420}
        footer={(
          <>
            <Button variant="secondary" onClick={() => setMemberToRemove(null)} className="mr-auto">Cancel</Button>
            <Button variant="destructive" onClick={removeMember}>Remove</Button>
          </>
        )}
      >
        {memberToRemove && (
          <p className="text-base leading-6 text-foreground">
            Are you sure you want to remove {memberToRemove.name} from this project?
          </p>
        )}
      </Modal>

      <Modal
        open={Boolean(roleChange)}
        onClose={() => setRoleChange(null)}
        title="Change role"
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
              Select a new role for {roleChange.member.name}.
            </p>
            <Select
              label="Role"
              value={roleChange.roleId}
              onChange={(event) => setRoleChange((current) =>
                current ? { ...current, roleId: event.target.value } : current,
              )}
              options={allRoles.map((role) => ({ value: role.id, label: role.name }))}
            />
          </div>
        )}
      </Modal>
    </section>
  )
}
