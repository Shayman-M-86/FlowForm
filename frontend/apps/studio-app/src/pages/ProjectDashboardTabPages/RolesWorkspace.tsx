import { useRef, useState } from 'react'
import { Badge, Button, Card, DropdownMenu, Toast } from '@flowform/ui'
import { RoleEditorModal, type RoleEditorState } from './RoleEditorModal'
import {
  PERMISSION_LABEL,
  normalizePermissionKeys,
  type CustomRole,
  type PermissionGroup,
  type PermissionKey,
  type RolePreset,
} from './roleDefinitions'
import { useRenderDebug } from '@/debug/useRenderDebug'

export type RoleFilter = 'all' | 'default' | 'custom'

export type PersistedRole = {
  id: number
  name: string
  permissions: unknown[]
  is_system_role: boolean
}

type RoleMutationInput = {
  name: string
  permissions: PermissionKey[]
}

interface RolesWorkspaceProps {
  title?: string
  defaultRoleDescription: string
  presets: RolePreset[]
  permissionGroups: PermissionGroup[]
  persistedRoles?: PersistedRole[]
  onCreateRole?: (role: RoleMutationInput) => Promise<void> | void
  onUpdateRole?: (roleId: number, role: RoleMutationInput) => Promise<void> | void
  onDeleteRole?: (roleId: number) => Promise<void> | void
  isSaving?: boolean
  isDeleting?: boolean
  readOnly?: boolean
}

const CARD_WIDTH = 220
const CARD_GAP = 16

export function RolesWorkspace({
  title = 'Roles',
  defaultRoleDescription,
  presets,
  permissionGroups,
  persistedRoles,
  onCreateRole,
  onUpdateRole,
  onDeleteRole,
  isSaving = false,
  isDeleting = false,
  readOnly = false,
}: RolesWorkspaceProps) {
  useRenderDebug('RolesWorkspace', { title, defaultRoleDescription, presets, permissionGroups, persistedRoles, isSaving, isDeleting })
  const [customRoles, setCustomRoles] = useState<CustomRole[]>([])
  const [editingRole, setEditingRole] = useState<RoleEditorState | null>(null)
  const [isNewRole, setIsNewRole] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all')
  const [roleFilterOpen, setRoleFilterOpen] = useState(false)
  const roleFilterTriggerRef = useRef<HTMLSpanElement>(null)
  const [rolePage, setRolePage] = useState(0)
  const [rolesPerPage, setRolesPerPage] = useState(4)
  const rolesObserverRef = useRef<ResizeObserver | null>(null)

  const rolesContainerRef = (el: HTMLDivElement | null) => {
    rolesObserverRef.current?.disconnect()
    if (!el) return
    const update = () => {
      const width = el.clientWidth
      const count = Math.max(1, Math.floor((width + CARD_GAP) / (CARD_WIDTH + CARD_GAP)))
      setRolesPerPage(count)
    }
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    rolesObserverRef.current = ro
  }

  const usesPersistedRoles = Boolean(persistedRoles)
  const allRoleCount = usesPersistedRoles ? (persistedRoles?.length ?? 0) : presets.length + customRoles.length
  const roleColumns = usesPersistedRoles
    ? (persistedRoles ?? []).map((role) => {
      const fallbackPreset = presets.find((preset) => preset.name.toLowerCase() === role.name.toLowerCase())
      return {
        id: String(role.id),
        name: role.name,
        description: fallbackPreset?.description ?? defaultRoleDescription,
        permissions: normalizePermissionKeys(role.permissions),
        custom: !role.is_system_role,
      }
    })
    : [
      ...presets.map((role) => ({
        ...role,
        custom: false,
      })),
      ...customRoles.map((role) => ({ ...role, custom: true })),
    ]
  const visibleRoleColumns = roleColumns.filter((role) => {
    if (roleFilter === 'default') return !role.custom
    if (roleFilter === 'custom') return role.custom
    return true
  })
  const roleFilterLabel = roleFilter === 'default' ? 'Default' : roleFilter === 'custom' ? 'Custom' : 'All'
  const roleTotalPages = Math.max(1, Math.ceil(visibleRoleColumns.length / rolesPerPage))
  const clampedRolePage = Math.min(rolePage, roleTotalPages - 1)
  const pagedRoleColumns = visibleRoleColumns.slice(clampedRolePage * rolesPerPage, (clampedRolePage + 1) * rolesPerPage)

  const addCustomRole = () => {
    const id = `custom-${Date.now()}`
    setActionError(null)
    setEditingRole({ id, custom: true, name: 'New role', description: defaultRoleDescription, permissions: new Set() })
    setIsNewRole(true)
  }

  const openRoleEditor = (role: (typeof roleColumns)[number]) => {
    setActionError(null)
    setEditingRole({
      id: role.id,
      custom: role.custom,
      name: role.name,
      description: role.description,
      permissions: new Set(role.permissions),
    })
    setIsNewRole(false)
  }

  const getActionErrorMessage = (error: unknown) => {
    if (error instanceof Error) return error.message
    if (typeof error === 'object' && error && 'message' in error && typeof error.message === 'string') return error.message
    return 'Role changes could not be saved.'
  }

  const saveRole = async () => {
    if (!editingRole) return
    const next = {
      name: editingRole.name.trim(),
      description: editingRole.description.trim(),
      permissions: normalizePermissionKeys([...editingRole.permissions]),
    }
    if (!next.name) return
    setActionError(null)

    try {
      if (usesPersistedRoles) {
        if (isNewRole) {
          await onCreateRole?.({ name: next.name, permissions: next.permissions })
          setRolePage(Math.floor(allRoleCount / rolesPerPage))
          if (roleFilter === 'default') setRoleFilter('all')
        } else if (editingRole.custom) {
          await onUpdateRole?.(Number(editingRole.id), { name: next.name, permissions: next.permissions })
        }
      } else if (editingRole.custom) {
        if (isNewRole) {
          setCustomRoles((current) => {
            const roles = [...current, { id: editingRole.id, ...next }]
            const newTotal = presets.length + roles.length
            setRolePage(Math.floor((newTotal - 1) / rolesPerPage))
            return roles
          })
          if (roleFilter === 'default') setRoleFilter('all')
        } else {
          setCustomRoles((current) =>
            current.map((role) => role.id === editingRole.id ? { ...role, ...next } : role),
          )
        }
      }
      setEditingRole(null)
      setIsNewRole(false)
    } catch (error) {
      setActionError(getActionErrorMessage(error))
    }
  }

  const deleteRole = async () => {
    if (!editingRole?.custom) return
    setActionError(null)
    try {
      if (usesPersistedRoles) {
        await onDeleteRole?.(Number(editingRole.id))
      } else {
        setCustomRoles((current) => current.filter((r) => r.id !== editingRole.id))
      }
      setEditingRole(null)
      setIsNewRole(false)
    } catch (error) {
      setActionError(getActionErrorMessage(error))
    }
  }

  return (
    <section className="grid gap-4">
      {actionError && (
        <Toast variant="error" onClose={() => setActionError(null)}>
          {actionError}
        </Toast>
      )}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold">{title}</h2>
          <p className="text-sm text-muted-foreground">{allRoleCount} roles</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {roleTotalPages > 1 && (
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setRolePage(clampedRolePage - 1)}
                disabled={clampedRolePage === 0}
                aria-label="Previous page"
              >
                ‹
              </Button>
              <span className="text-xs text-muted-foreground">{clampedRolePage + 1} / {roleTotalPages}</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setRolePage(clampedRolePage + 1)}
                disabled={clampedRolePage >= roleTotalPages - 1}
                aria-label="Next page"
              >
                ›
              </Button>
            </div>
          )}
          <span ref={roleFilterTriggerRef} className="inline-flex">
            <Button
              variant="secondary"
              size="sm"
              aria-haspopup="menu"
              aria-expanded={roleFilterOpen}
              onClick={() => setRoleFilterOpen((open) => !open)}
            >
              <span>{roleFilterLabel}</span>
              <span aria-hidden="true" className="text-[0.7rem] leading-none text-muted-foreground">▾</span>
            </Button>
          </span>
          <DropdownMenu
            open={roleFilterOpen}
            onClose={() => setRoleFilterOpen(false)}
            trigger={roleFilterTriggerRef}
            align="right"
            buttonAlign="right"
            size="auto"
            fullscreenAt="never"
            sections={[{
              actions: [
                { key: 'all', content: 'All', onSelect: () => { setRoleFilter('all'); setRolePage(0) } },
                { key: 'default', content: 'Default', onSelect: () => { setRoleFilter('default'); setRolePage(0) } },
                { key: 'custom', content: 'Custom', onSelect: () => { setRoleFilter('custom'); setRolePage(0) } },
              ],
            }]}
          />
          {!readOnly && (
            <Button variant="primary" size="sm" icon="plus" onClick={addCustomRole}>
              Add role
            </Button>
          )}
        </div>
      </div>

      <div ref={rolesContainerRef} className="w-full flex justify-center overflow-hidden">
        <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${pagedRoleColumns.length}, ${CARD_WIDTH}px)` }}>
          {pagedRoleColumns.map((role) => (
            <Card key={role.id} size="sm">
              <div className="flex h-full flex-col gap-3">
                <div className="flex min-h-[128px] items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="ml-1 line-clamp-2 text-sm font-semibold leading-snug text-foreground">{role.name}</p>
                    <div className="mt-1">
                      <Badge variant={role.custom ? 'accent' : 'muted'} size="xxs">
                        {role.custom ? 'Custom' : 'Default'}
                      </Badge>
                    </div>
                    <p className="ml-1 mt-1 line-clamp-3 text-xs leading-relaxed text-muted-foreground">
                      {role.description}
                    </p>
                  </div>
                  {role.custom && !readOnly ? (
                    <Button variant="secondary" size="sm" onClick={() => openRoleEditor(role)}>
                      Edit
                    </Button>
                  ) : null}
                </div>
                <div className="flex flex-col gap-3 border-t border-border pt-3">
                  <p className="text-xs font-semibold text-foreground">Permissions</p>
                  {permissionGroups.map((group) => (
                    <div key={group.label}>
                      <p className="mb-1.5 text-[0.68rem] font-semibold uppercase tracking-wider text-muted-foreground">
                        {group.label}
                      </p>
                      <div className="flex flex-col gap-1.5">
                        {group.permissions.map((permission) => {
                          const allowed = role.permissions.includes(permission)
                          return (
                            <div
                              key={permission}
                              className={`flex items-center gap-2 text-xs ${allowed ? 'text-foreground' : 'text-muted-foreground opacity-45'}`}
                            >
                              <span
                                aria-hidden="true"
                                className={`grid size-4 shrink-0 place-items-center rounded-full border text-[0.62rem] ${allowed ? 'border-accent/30 bg-accent/15 text-accent' : 'border-border text-muted-foreground'}`}
                              >
                                {allowed ? '✓' : '–'}
                              </span>
                              <span>{PERMISSION_LABEL[permission]}</span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      <RoleEditorModal
        role={editingRole}
        permissionGroups={permissionGroups}
        onClose={() => {
          setEditingRole(null)
          setIsNewRole(false)
        }}
        onChange={setEditingRole}
        onSave={saveRole}
        onDelete={deleteRole}
        isNew={isNewRole}
        showDescription={!usesPersistedRoles}
        isSaving={isSaving}
        isDeleting={isDeleting}
      />
    </section>
  )
}
