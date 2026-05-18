import { useCallback, useMemo, useRef, useState } from 'react'
import { Button, Badge, Input, Modal, Select, Table, type TableColumn } from '@flowform/ui'
import { mockProjectMembers, type MockProjectMember } from '@/api/mockData'
import { PERMISSION_GROUPS, PRESET_ROLES, type CustomRole } from './RolesTab'
import {
  DEFAULT_PROJECT_INVITE_ROLE_ID,
  PROJECT_MEMBER_ROLE_TO_ROLE_ID,
} from './roleDefinitions'
import { RoleEditorModal, type RoleEditorState } from './RoleEditorModal'
import { useRenderDebug } from '@/debug/useRenderDebug'
import { MemberRoleActions } from '@/components/MemberRoleActions'
import { PermissionBadge } from '@/components/PermissionBadge'
import { RoleBadgePreview } from '@/components/RoleBadgePreview'

export function MembersTab() {
  useRenderDebug('MembersTab')
  const [members, setMembers] = useState<MockProjectMember[]>(mockProjectMembers)
  const [memberToRemove, setMemberToRemove] = useState<MockProjectMember | null>(null)

  // ── Invite modal ────────────────────────────────────────────────────────────
  const [inviteOpen, setInviteOpen] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newRoleId, setNewRoleId] = useState(DEFAULT_PROJECT_INVITE_ROLE_ID)

  // ── Role editor modal (nested) ──────────────────────────────────────────────
  const [customRoles, setCustomRoles] = useState<CustomRole[]>([])
  const [editingRole, setEditingRole] = useState<RoleEditorState | null>(null)
  const [roleEditorReturnTo, setRoleEditorReturnTo] = useState<'invite' | null>(null)
  const selectCreatedRoleRef = useRef<((roleId: string) => void) | null>(null)

  const allRoles = useMemo(() => [
    ...PRESET_ROLES,
    ...customRoles,
  ], [customRoles])

  const addCustomRole = (returnTo: 'invite' | null = 'invite', selectRole?: (roleId: string) => void) => {
    const id = `custom-${Date.now()}`
    selectCreatedRoleRef.current = selectRole ?? null
    setRoleEditorReturnTo(returnTo)
    setEditingRole({ id, custom: true, name: 'New role', description: 'Custom project role.', permissions: new Set() })
    if (returnTo === 'invite') {
      setInviteOpen(false)
    }
  }

  const saveRole = () => {
    if (!editingRole) return
    const roleId = editingRole.id
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
    if (selectCreatedRoleRef.current) {
      selectCreatedRoleRef.current(roleId)
      selectCreatedRoleRef.current = null
    } else {
      setNewRoleId(roleId)
    }
    setEditingRole(null)
    if (roleEditorReturnTo === 'invite') {
      setInviteOpen(true)
    }
    setRoleEditorReturnTo(null)
  }

  const deleteRole = () => {
    if (!editingRole?.custom) return
    setCustomRoles((c) => c.filter((r) => r.id !== editingRole.id))
    if (newRoleId === editingRole.id) setNewRoleId(DEFAULT_PROJECT_INVITE_ROLE_ID)
    setEditingRole(null)
    selectCreatedRoleRef.current = null
    setRoleEditorReturnTo(null)
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

  const changeMemberRole = useCallback((memberToUpdate: MockProjectMember, roleId: string) => {
    const role = allRoles.find((r) => r.id === roleId)
    if (!role) return
    setMembers((c) =>
      c.map((member) =>
        member.id === memberToUpdate.id
          ? { ...member, role: role.name as MockProjectMember['role'] }
          : member,
      ),
    )
  }, [allRoles])

  const renderProjectPermissions = useCallback((roleId: string) => {
    const role = allRoles.find((r) => r.id === roleId)
    if (!role) return null

    return (
      <div className="flex flex-wrap gap-1.5">
        {role.permissions.map((permission) => (
          <PermissionBadge key={permission} permission={permission} />
        ))}
      </div>
    )
  }, [allRoles])

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
      cell: (row) => {
        const role = allRoles.find((candidate) => candidate.id === PROJECT_MEMBER_ROLE_TO_ROLE_ID[row.role])
        return (
          <RoleBadgePreview
            label={row.role}
            permissions={(role?.permissions ?? []).map((permission) => ({ key: permission }))}
          />
        )
      },
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
        <MemberRoleActions
          memberName={row.name}
          memberEmail={row.email}
          editRoleLabel="Edit project role"
          roles={allRoles}
          selectedRoleId={PROJECT_MEMBER_ROLE_TO_ROLE_ID[row.role]}
          onSaveRole={(roleId) => changeMemberRole(row, roleId)}
          onAddRole={(selectRole) => addCustomRole(null, selectRole)}
          renderEffectivePreview={renderProjectPermissions}
          extraActions={[
            {
              key: 'remove-member',
              label: 'Remove member',
              variant: 'destructive',
              onSelect: () => setMemberToRemove(row),
            },
          ]}
        />
      ),
    },
  ], [addCustomRole, allRoles, changeMemberRole, renderProjectPermissions])

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <section className="grid gap-4">
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
        className='max-w-6xl mx-auto'
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
            <Button variant="secondary" size="md" onClick={() => addCustomRole('invite')}>
              New role
            </Button>
          </div>
        </div>
      </Modal>

      <RoleEditorModal
        role={editingRole}
        onClose={() => {
          setEditingRole(null)
          selectCreatedRoleRef.current = null
          if (roleEditorReturnTo === 'invite') {
            setInviteOpen(true)
          }
          setRoleEditorReturnTo(null)
        }}
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

    </section>
  )
}
