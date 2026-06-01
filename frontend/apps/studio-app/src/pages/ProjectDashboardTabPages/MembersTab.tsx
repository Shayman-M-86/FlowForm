import { useCallback, useMemo, useRef, useState } from 'react'
import { Button, Badge, Card, Input, LargeInput, Modal, Select, Spinner, Table, Toast, type TableColumn } from '@flowform/ui'
import { useProjectMembers, useProjectInvitations, useSendInvitation, useDeleteProjectMember, useRevokeInvitation, useUpdateProjectMember } from '@/api/hooks/members'
import type { ProjectInvitationOut, ProjectMemberOut } from '@/api/hooks/members'
import { getInviteErrorMessage } from '@/api/errors'
import { RoleEditorModal, type RoleEditorState } from './RoleEditorModal'
import type { CustomRole } from './RolesTab'
import { normalizePermissionKeys, type PermissionKey } from './roleDefinitions'
import { useRenderDebug } from '@/debug/useRenderDebug'
import { MemberRoleActions } from '@/components/MemberRoleActions'
import { PermissionBadge } from '@/components/PermissionBadge'
import { RoleBadgePreview } from '@/components/RoleBadgePreview'
import { PERMISSION_GROUPS } from './RolesTab'
import { useProjectRoles, useCreateProjectRole } from '@/api/hooks/roles'
import { useHasProjectPermission } from '@/api/hooks/permissions'

type Props = { projectId: number }
type ProjectMemberRole = CustomRole & { isSystemRole: boolean }

function projectRoleIdFromUiId(roleId: string) {
  const parsed = Number(roleId)
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null
}

export function MembersTab({ projectId }: Props) {
  useRenderDebug('MembersTab')

  const canManageMembers = useHasProjectPermission(projectId, 'project:manage_members')
  const canManageRoles = useHasProjectPermission(projectId, 'project:manage_roles')
  const { data: members = [], isLoading } = useProjectMembers(projectId)
  const { data: invitations = [] } = useProjectInvitations(projectId)
  const { data: projectRoles = [], isLoading: rolesLoading } = useProjectRoles(projectId)
  const createProjectRole = useCreateProjectRole(projectId)
  const sendInvitation = useSendInvitation(projectId)
  const updateMember = useUpdateProjectMember(projectId)
  const deleteMember = useDeleteProjectMember(projectId)
  const revokeInvitation = useRevokeInvitation(projectId)

  const [memberToRemove, setMemberToRemove] = useState<ProjectMemberOut | null>(null)
  const [invitationToRevoke, setInvitationToRevoke] = useState<ProjectInvitationOut | null>(null)
  const [inviteSentTo, setInviteSentTo] = useState<string | null>(null)

  // ── Invite modal ────────────────────────────────────────────────────────────
  const [inviteOpen, setInviteOpen] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newMessage, setNewMessage] = useState('')
  const [newRoleId, setNewRoleId] = useState('')

  // ── Role editor modal (nested) ──────────────────────────────────────────────
  const [customRoles, setCustomRoles] = useState<CustomRole[]>([])
  const [editingRole, setEditingRole] = useState<RoleEditorState | null>(null)
  const [roleEditorReturnTo, setRoleEditorReturnTo] = useState<'invite' | null>(null)
  const selectCreatedRoleRef = useRef<((roleId: string) => void) | null>(null)

  const persistedRoles = useMemo<ProjectMemberRole[]>(() => projectRoles.map((role) => ({
    id: String(role.id),
    name: role.name,
    description: role.is_system_role ? 'System project role.' : 'Custom project role.',
    permissions: normalizePermissionKeys(role.permissions),
    isSystemRole: role.is_system_role,
  })), [projectRoles])
  const localCustomRoles = useMemo<ProjectMemberRole[]>(() => customRoles.map((role) => ({
    ...role,
    isSystemRole: false,
  })), [customRoles])
  const allRoles = useMemo(() => [...persistedRoles, ...localCustomRoles], [localCustomRoles, persistedRoles])
  const assignableRoles = useMemo(() => allRoles.filter((role) => !role.isSystemRole), [allRoles])
  const roleById = useMemo(() => new Map(allRoles.map((role) => [role.id, role])), [allRoles])
  const assignableRoleById = useMemo(() => new Map(assignableRoles.map((role) => [role.id, role])), [assignableRoles])
  const selectedInviteRoleId = newRoleId && assignableRoleById.has(newRoleId) ? newRoleId : assignableRoles[0]?.id ?? ''

  const addCustomRole = useCallback((returnTo: 'invite' | null = 'invite', selectRole?: (roleId: string) => void) => {
    const id = `custom-${Date.now()}`
    selectCreatedRoleRef.current = selectRole ?? null
    setRoleEditorReturnTo(returnTo)
    setEditingRole({ id, custom: true, name: 'New role', description: 'Custom project role.', permissions: new Set<PermissionKey>() })
    if (returnTo === 'invite') setInviteOpen(false)
  }, [])

  const saveRole = async () => {
    if (!editingRole) return
    const next = {
      name: editingRole.name.trim(),
      description: editingRole.description.trim(),
      permissions: [...editingRole.permissions] as PermissionKey[],
    }
    if (!next.name) return

    let resolvedId = editingRole.id
    if (editingRole.custom) {
      try {
        const created = await createProjectRole.mutateAsync({ name: next.name, permissions: next.permissions })
        resolvedId = String(created.id)
      } catch {
        return
      }
    }

    setCustomRoles((c) =>
      c.some((r) => r.id === editingRole.id)
        ? c.map((r) => r.id === editingRole.id ? { ...r, ...next, id: resolvedId } : r)
        : [...c, { id: resolvedId, ...next }],
    )
    if (selectCreatedRoleRef.current) {
      selectCreatedRoleRef.current(resolvedId)
      selectCreatedRoleRef.current = null
    } else {
      setNewRoleId(resolvedId)
    }
    setEditingRole(null)
    if (roleEditorReturnTo === 'invite') setInviteOpen(true)
    setRoleEditorReturnTo(null)
  }

  const deleteRole = () => {
    if (!editingRole?.custom) return
    setCustomRoles((c) => c.filter((r) => r.id !== editingRole.id))
    if (newRoleId === editingRole.id) setNewRoleId('')
    setEditingRole(null)
    selectCreatedRoleRef.current = null
    setRoleEditorReturnTo(null)
  }

  // ── Invite submit ───────────────────────────────────────────────────────────
  const sendInvite = () => {
    const email = newEmail.trim()
    if (!email) return
    const roleId = projectRoleIdFromUiId(selectedInviteRoleId)
    sendInvitation.mutate(
      { email, role_id: roleId, invite_message: newMessage.trim() || null },
      {
        onSuccess: () => {
          setInviteSentTo(email)
          setNewEmail('')
          setNewMessage('')
          setInviteOpen(false)
        },
      },
    )
  }

  const removeMember = () => {
    if (!memberToRemove) return
    deleteMember.mutate(memberToRemove.id, {
      onSuccess: () => setMemberToRemove(null),
    })
  }

  const doRevokeInvitation = () => {
    if (!invitationToRevoke) return
    revokeInvitation.mutate(invitationToRevoke.id, {
      onSuccess: () => setInvitationToRevoke(null),
    })
  }

  const renderProjectPermissions = useCallback((roleId: string) => {
    const role = roleById.get(roleId)
    if (!role) return null
    return (
      <div className="flex flex-wrap gap-1.5">
        {role.permissions.map((permission) => (
          <PermissionBadge key={permission} permission={permission} />
        ))}
      </div>
    )
  }, [roleById])

  // ── Table columns ───────────────────────────────────────────────────────────
  const memberColumns = useMemo<TableColumn<ProjectMemberOut>[]>(() => [
    {
      key: 'member',
      header: 'Member',
      minWidth: 200,
      cell: (row) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">
            {row.user.display_name ?? row.user.email}
          </p>
          <p className="truncate text-xs text-muted-foreground">{row.user.email}</p>
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      minWidth: 100,
      cell: (row) => {
        const role = roleById.get(String(row.role_id ?? ''))
        const variant = role?.isSystemRole ? 'accent' : 'default'
        return (
          <RoleBadgePreview
            label={role?.name ?? '—'}
            permissions={(role?.permissions ?? []).map((permission) => ({ key: permission }))}
            variant={variant}
          />
        )
      },
    },
    {
      key: 'status',
      header: 'Status',
      minWidth: 100,
      cell: (row) => (
        <Badge variant={row.status === 'active' ? 'success' : 'warning'} size="xs">
          {row.status === 'active' ? 'Active' : 'Suspended'}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      minWidth: 50,
      maxWidth: 50,
      headerClassName: 'flex justify-center text-right pr-2',
      cellClassName: 'flex justify-center px-0',
      cell: (row) => {
        const role = roleById.get(String(row.role_id ?? ''))
        if (role?.isSystemRole || !canManageMembers) return null
        return (
          <MemberRoleActions
            memberName={row.user.display_name ?? row.user.email}
            memberEmail={row.user.email}
            editRoleLabel="Edit project role"
            roles={assignableRoles}
            selectedRoleId={row.role_id === null ? undefined : String(row.role_id)}
            onSaveRole={(roleId) => {
              const projectRoleId = projectRoleIdFromUiId(roleId)
              if (projectRoleId === null) return
              updateMember.mutate({
                membershipId: row.id,
                body: { role_id: projectRoleId, status: null },
              })
            }}
            onAddRole={canManageRoles ? (selectRole) => addCustomRole(null, selectRole) : undefined}
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
        )
      },
    },
  ], [addCustomRole, assignableRoles, renderProjectPermissions, roleById, updateMember])

  const invitationColumns = useMemo<TableColumn<ProjectInvitationOut>[]>(() => [
    {
      key: 'email',
      header: 'Email',
      minWidth: 120,
      cell: (row) => (
        <p className="truncate text-xs text-foreground">{row.invited_email}</p>
      ),
    },
    {
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      minWidth: 90,
      maxWidth: 90,
      headerClassName: 'flex justify-center text-right pr-2',
      cellClassName: 'flex justify-center px-0',
      cell: (row) => canManageMembers ? (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setInvitationToRevoke(row)}
        >
          Revoke
        </Button>
      ) : null,
    },
  ], [])

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <section className="grid gap-4">
      {inviteSentTo && (
        <Toast variant="success" onClose={() => setInviteSentTo(null)}>
          Invitation sent to {inviteSentTo}.
        </Toast>
      )}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Members</h2>
          <p className="text-sm text-muted-foreground">{members.length} total</p>
        </div>
        {canManageMembers && (
          <Button variant="primary" size="sm" icon="plus" onClick={() => setInviteOpen(true)}>
            Invite member
          </Button>
        )}
      </div>

      {/* ── Two-column layout: members table + invitations card ─────────────── */}
      <div className="flex flex-col xl:flex-row gap-6 items-start">

        {/* Members table — grows to fill available space */}
        <div className="min-w-0 w-full flex-1">
          {isLoading || rolesLoading ? (
            <div className="flex justify-center py-10"><Spinner size={24} /></div>
          ) : (
            <Table
              columns={memberColumns}
              rows={members}
              getRowKey={(row) => row.id}
            />
          )}
        </div>

        {/* Invitations card — fixed width, stacks below on small screens */}
        <Card size="sm" tone="muted" className="w-full xl:w-92 shrink-0">
          <div className="flex items-baseline justify-between gap-2 mb-3">
            <h3 className="text-sm font-semibold">Pending invitations</h3>
            {invitations.length > 0 && (
              <Badge variant="warning" size="xs">{invitations.length}</Badge>
            )}
          </div>

          {invitations.length === 0 ? (
            <p className="text-xs text-muted-foreground leading-relaxed">
              Invitations you send will appear here until accepted or revoked.
            </p>
          ) : (
            <Table
              columns={invitationColumns}
              rows={invitations}
              getRowKey={(row) => row.id}
              hideHeader
            />
          )}
        </Card>
      </div>

      {/* ── Invite modal ─────────────────────────────────────────────────────── */}
      <Modal
        open={inviteOpen}
        onClose={() => { setInviteOpen(false); setNewMessage('') }}
        title="Invite member"
        width={780}
        footer={(
          <>
            <Button variant="secondary" onClick={() => { setInviteOpen(false); setNewMessage('') }}>Cancel</Button>
            <Button
              variant="primary"
              onClick={sendInvite}
              disabled={!newEmail.trim() || sendInvitation.isPending}
            >
              {sendInvitation.isPending ? 'Sending…' : 'Send invite'}
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
            maxLength={254}
            hint={`${newEmail.length}/254`}
          />
          <div className="flex items-end gap-2">
            <div className="flex-0">
              <Select
                label="Role"
                value={selectedInviteRoleId}
                className='w-50'
                onChange={(e) => setNewRoleId(e.target.value)}
                options={assignableRoles.map((r) => ({ value: r.id, label: r.name }))}
              />
            </div>
            {canManageRoles && (
              <Button variant="secondary" size="md" onClick={() => addCustomRole('invite')}>
                New role
              </Button>
            )}
          </div>
          <LargeInput
            label="Message (optional)"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder="Add a personal note to your invitation…"
            maxText={500}
            showCount
            autoGrow
            rows={3}
          />
          {sendInvitation.isError && (
            <p className="text-sm text-destructive">
              {getInviteErrorMessage(sendInvitation.error)}
            </p>
          )}
        </div>
      </Modal>

      <RoleEditorModal
        role={editingRole}
        onClose={() => {
          setEditingRole(null)
          selectCreatedRoleRef.current = null
          if (roleEditorReturnTo === 'invite') setInviteOpen(true)
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
            <Button
              variant="destructive"
              onClick={removeMember}
              disabled={deleteMember.isPending}
            >
              {deleteMember.isPending ? 'Removing…' : 'Remove'}
            </Button>
          </>
        )}
      >
        {memberToRemove && (
          <p className="text-base leading-6 text-foreground">
            Are you sure you want to remove {memberToRemove.user.display_name ?? memberToRemove.user.email} from this project?
          </p>
        )}
      </Modal>

      <Modal
        open={Boolean(invitationToRevoke)}
        onClose={() => setInvitationToRevoke(null)}
        title="Revoke invitation"
        width={420}
        footer={(
          <>
            <Button variant="secondary" onClick={() => setInvitationToRevoke(null)} className="mr-auto">Cancel</Button>
            <Button
              variant="destructive"
              onClick={doRevokeInvitation}
              disabled={revokeInvitation.isPending}
            >
              {revokeInvitation.isPending ? 'Revoking…' : 'Revoke'}
            </Button>
          </>
        )}
      >
        {invitationToRevoke && (
          <p className="text-base leading-6 text-foreground">
            Revoke the invitation for {invitationToRevoke.invited_email}? They will no longer be able to accept it.
          </p>
        )}
      </Modal>
    </section>
  )
}
