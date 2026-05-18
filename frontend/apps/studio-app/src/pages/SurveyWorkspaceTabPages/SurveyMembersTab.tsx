import { useMemo, useRef, useState } from 'react'
import { Badge, Button, DropdownMenu, Table, type TableColumn } from '@flowform/ui'
import { mockProjectMembers, type MockProjectMember } from '@/api/mockData'
import { useRenderDebug } from '@/debug/useRenderDebug'
import { MemberRoleActions } from '@/components/MemberRoleActions'
import { PermissionBadge } from '@/components/PermissionBadge'
import { RoleBadgePreview } from '@/components/RoleBadgePreview'
import { RoleEditorModal, type RoleEditorState } from '../ProjectDashboardTabPages/RoleEditorModal'
import {
  DEFAULT_SURVEY_ROLE_ASSIGNMENTS,
  PROJECT_ROLE_TO_SURVEY_ROLE_ID,
  SURVEY_PERMISSION_GROUPS,
  SURVEY_PRESET_ROLES,
  permissionsGained,
  roleForId,
  rolePermissions,
  type CustomRole,
  type PermissionKey,
  type RoleWithPermissions,
} from '../ProjectDashboardTabPages/roleDefinitions'

type SurveyRoleOption = RoleWithPermissions

type PermissionPreview = {
  key: PermissionKey
  variant: 'default' | 'warning'
}

interface MemberRow extends MockProjectMember {
  overrideRoleId?: string
  effectiveRoleId: string
}

function PermissionBadges({ permissions }: { permissions: PermissionPreview[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {permissions.map((permission) => (
        <PermissionBadge
          key={permission.key}
          permission={permission.key}
          variant={permission.variant}
        />
      ))}
    </div>
  )
}

function CompactPermissionBadges({
  permissions,
  limit = 3,
}: {
  permissions: PermissionPreview[]
  limit?: number
}) {
  const triggerRef = useRef<HTMLSpanElement>(null)
  const [open, setOpen] = useState(false)
  const visiblePermissions = permissions.slice(0, limit)
  const hiddenPermissions = permissions.slice(limit)

  return (
    <div className="flex flex-wrap gap-1.5">
      {visiblePermissions.map((permission) => (
        <PermissionBadge
          key={permission.key}
          permission={permission.key}
          variant={permission.variant}
        />
      ))}
      {hiddenPermissions.length > 0 && (
        <>
          <span ref={triggerRef} className="inline-flex">
            <Badge
              variant="muted"
              size="xs"
              onClick={() => setOpen((current) => !current)}
            >
              +{hiddenPermissions.length} more
            </Badge>
          </span>
          <DropdownMenu
            open={open}
            onClose={() => setOpen(false)}
            trigger={triggerRef}
            width="18rem"
            align="auto"
            direction="auto"
            fullscreenAt="never"
            sections={[
              {
                actions: [
                  {
                    key: 'all-permissions',
                    closeOnSelect: false,
                    content: (
                      <div className="grid w-full gap-3 rounded-sm px-3 py-2 text-left">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-foreground">Effective permissions</p>
                          <p className="text-xs text-muted-foreground">All permissions available to this member</p>
                        </div>
                        <PermissionBadges permissions={permissions} />
                      </div>
                    ),
                  },
                ],
              },
            ]}
          />
        </>
      )}
    </div>
  )
}

export function SurveyMembersTab() {
  useRenderDebug('SurveyMembersTab')
  const [surveyRoleAssignments, setSurveyRoleAssignments] = useState<Record<number, string>>(
    DEFAULT_SURVEY_ROLE_ASSIGNMENTS,
  )
  const [customSurveyRoles, setCustomSurveyRoles] = useState<CustomRole[]>([])
  const [editingRole, setEditingRole] = useState<RoleEditorState | null>(null)
  const selectCreatedRoleRef = useRef<((roleId: string) => void) | null>(null)

  const surveyRoles = useMemo<SurveyRoleOption[]>(
    () => [...SURVEY_PRESET_ROLES, ...customSurveyRoles],
    [customSurveyRoles],
  )

  const rows = useMemo<MemberRow[]>(
    () =>
      mockProjectMembers.map((member) => {
        const overrideRoleId = surveyRoleAssignments[member.id]
        return {
          ...member,
          overrideRoleId,
          effectiveRoleId: overrideRoleId ?? PROJECT_ROLE_TO_SURVEY_ROLE_ID[member.role],
        }
      }),
    [surveyRoleAssignments],
  )

  const addSurveyRole = (selectRole: (roleId: string) => void) => {
    const id = `survey-custom-${Date.now()}`
    selectCreatedRoleRef.current = selectRole
    setEditingRole({
      id,
      custom: true,
      name: 'New survey role',
      description: 'Custom survey role.',
      permissions: new Set(),
    })
  }

  const saveSurveyRole = () => {
    if (!editingRole) return
    const next = {
      name: editingRole.name.trim(),
      description: editingRole.description.trim(),
      permissions: [...editingRole.permissions],
    }
    if (!next.name) return
    setCustomSurveyRoles((current) =>
      current.some((role) => role.id === editingRole.id)
        ? current.map((role) => role.id === editingRole.id ? { ...role, ...next } : role)
        : [...current, { id: editingRole.id, ...next }],
    )
    selectCreatedRoleRef.current?.(editingRole.id)
    selectCreatedRoleRef.current = null
    setEditingRole(null)
  }

  const deleteSurveyRole = () => {
    if (!editingRole?.custom) return
    setCustomSurveyRoles((current) => current.filter((role) => role.id !== editingRole.id))
    setSurveyRoleAssignments((current) => {
      const next = { ...current }
      for (const [memberId, roleId] of Object.entries(next)) {
        if (roleId === editingRole.id) {
          delete next[Number(memberId)]
        }
      }
      return next
    })
    selectCreatedRoleRef.current = null
    setEditingRole(null)
  }

  const surveyPermissionPreview = (member: MemberRow, roleId: string): PermissionPreview[] => {
    const gained = permissionsGained(surveyRoles, PROJECT_ROLE_TO_SURVEY_ROLE_ID[member.role], roleId)

    return rolePermissions(surveyRoles, roleId).map((permission) => ({
      key: permission,
      variant: gained.includes(permission) ? 'warning' : 'default',
    }))
  }

  const renderSurveyPermissions = (member: MemberRow, roleId: string) => {
    return <PermissionBadges permissions={surveyPermissionPreview(member, roleId)} />
  }

  const columns: TableColumn<MemberRow>[] = [
    {
      key: 'member',
      header: 'Member',
      minWidth: 100,
      maxWidth: 200,
      cell: (member) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">{member.name}</p>
          <p className="truncate text-2xs text-muted-foreground">{member.email}</p>
        </div>
      ),
    },
    {
      key: 'project-role',
      header: 'Project role',
      minWidth: 65,
      maxWidth: 150,
      cell: (member) => (
        <RoleBadgePreview
          label={member.role}
          permissions={rolePermissions(surveyRoles, PROJECT_ROLE_TO_SURVEY_ROLE_ID[member.role]).map(
            (permission) => ({ key: permission }),
          )}
        />
      ),
    },
    {
      key: 'survey-role',
      header: 'Survey role',
      minWidth: 75,
      maxWidth: 150,
      cell: (member) => {
        const gained = permissionsGained(
          surveyRoles,
          PROJECT_ROLE_TO_SURVEY_ROLE_ID[member.role],
          member.effectiveRoleId,
        )
        if (!member.overrideRoleId || gained.length === 0) {
          return <span className="text-xs text-muted-foreground">-</span>
        }
        const role = roleForId(surveyRoles, member.overrideRoleId)
        return (
          <RoleBadgePreview
            label={role?.name ?? 'Custom role'}
            prefix="+"
            variant="warning"
            permissions={gained.map((permission) => ({
              key: permission,
              variant: 'warning',
            }))}
          />
        )
      },
    },
    {
      key: 'effective',
      header: 'Effective permissions',
      minWidth: 110,
      cell: (member) => (
        <CompactPermissionBadges permissions={surveyPermissionPreview(member, member.effectiveRoleId)} />
      ),
    },
    {
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      minWidth: 50,
      maxWidth: 50,
      headerClassName: 'flex justify-center text-right pr-2',
      cellClassName: 'flex justify-center px-0',
      cell: (member) => (
        <MemberRoleActions
          memberName={member.name}
          memberEmail={member.email}
          editRoleLabel="Edit survey role"
          roles={surveyRoles}
          selectedRoleId={member.overrideRoleId ?? member.effectiveRoleId}
          onSaveRole={(roleId) =>
            setSurveyRoleAssignments((current) => ({ ...current, [member.id]: roleId }))
          }
          onRemoveRole={
            member.overrideRoleId
              ? () =>
                  setSurveyRoleAssignments((current) => {
                    const next = { ...current }
                    delete next[member.id]
                    return next
                  })
              : undefined
          }
          removeRoleLabel="Remove survey role"
          onAddRole={addSurveyRole}
          renderEffectivePreview={(roleId) => renderSurveyPermissions(member, roleId)}
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

      <div className="w-full max-w-[1100px] justify-self-center">
        <Table
          columns={columns}
          rows={rows}
          getRowKey={(member) => member.id}
        />
      </div>

      <RoleEditorModal
        role={editingRole}
        onClose={() => {
          setEditingRole(null)
          selectCreatedRoleRef.current = null
        }}
        onChange={setEditingRole}
        onSave={saveSurveyRole}
        onDelete={deleteSurveyRole}
        permissionGroups={SURVEY_PERMISSION_GROUPS}
        isNew
      />
    </section>
  )
}
