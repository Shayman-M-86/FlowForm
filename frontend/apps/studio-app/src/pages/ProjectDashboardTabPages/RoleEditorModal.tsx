import { Badge, Button, Input, LargeInput, Modal, Tooltip } from '@flowform/ui'
import { PERMISSION_LABEL, PERMISSION_TOOLTIP, type PermissionGroup, type PermissionKey } from './roleDefinitions'
import { useRenderDebug } from '@/debug/useRenderDebug'

export type RoleEditorState = {
  id: string
  custom: boolean
  name: string
  description: string
  permissions: Set<PermissionKey>
}

interface RoleEditorModalProps {
  role: RoleEditorState | null
  onClose: () => void
  onChange: (role: RoleEditorState) => void
  onSave: () => void | Promise<void>
  onDelete?: () => void
  isNew?: boolean
  permissionGroups: PermissionGroup[]
  showDescription?: boolean
  isSaving?: boolean
  isDeleting?: boolean
}

export function RoleEditorModal({
  role,
  onClose,
  onChange,
  onSave,
  onDelete,
  isNew = false,
  permissionGroups,
  showDescription = true,
  isSaving = false,
  isDeleting = false,
}: RoleEditorModalProps) {
  useRenderDebug('RoleEditorModal', { role, onClose, onChange, onSave, onDelete, isNew, permissionGroups, showDescription, isSaving, isDeleting })
  const togglePermission = (permission: PermissionKey) => {
    if (!role) return
    const permissions = new Set(role.permissions)
    if (permissions.has(permission)) permissions.delete(permission)
    else permissions.add(permission)
    onChange({ ...role, permissions })
  }

  return (
    <Modal
      open={Boolean(role)}
      onClose={onClose}
      title={isNew ? "New role" : "Edit role"}
      width={760}
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} className="mr-auto">Cancel</Button>
          {!isNew && role?.custom && onDelete && (
            <Button variant="danger" onClick={onDelete} disabled={isDeleting || isSaving}>Delete</Button>
          )}
          <Button
            variant="primary"
            onClick={onSave}
            disabled={isSaving || isDeleting || !role?.name.trim() || (role?.permissions.size ?? 0) === 0}
          >
            Save
          </Button>
        </>
      )}
    >
      {role && (
        <div className="grid gap-5">
          <div className="grid gap-3  p-1">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <Input
                  label="Role name"
                  type="text"
                  value={role.name}
                  onChange={(e) => onChange({ ...role, name: e.target.value })}
                  placeholder="Role name"
                />
                <div className="mt-2">
                  <Badge variant={role.custom ? 'accent' : 'muted'} size="xxs">
                    {role.custom ? 'Custom' : 'Default'}
                  </Badge>
                </div>
              </div>
            </div>
            {showDescription && (
              <LargeInput
                label="Description"
                rows={3}
                value={role.description}
                onChange={(e) => onChange({ ...role, description: e.target.value })}
                placeholder="Role description"
              />
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            {permissionGroups.map((group) => (
              <section key={group.label} className="rounded-xl border border-border p-4">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {group.label}
                </p>
                <div className="flex flex-col gap-2">
                  {group.permissions.map((permission) => {
                    const checked = role.permissions.has(permission)
                    return (
                      <label
                        key={permission}
                        className={`flex cursor-pointer items-center gap-2 text-xs ${checked ? 'text-foreground' : 'text-muted-foreground'}`}
                      >
                        <input
                          type="checkbox"
                          className="size-3.5 cursor-pointer rounded border-border accent-primary"
                          checked={checked}
                          onChange={() => togglePermission(permission)}
                        />
                        <Tooltip title={PERMISSION_TOOLTIP[permission]} size="sm">
                          <span>{PERMISSION_LABEL[permission]}</span>
                        </Tooltip>
                      </label>
                    )
                  })}
                </div>
              </section>
            ))}
          </div>
        </div>
      )}
    </Modal>
  )
}
