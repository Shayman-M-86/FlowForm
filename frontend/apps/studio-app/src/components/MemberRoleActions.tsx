import { useRef, useState, type MouseEventHandler, type ReactNode } from 'react'
import { Badge, Button, DropdownMenu, Modal, Select } from '@flowform/ui'
import { Trash2, UserCog } from 'lucide-react'

export type MemberRoleOption = {
  id: string
  name: string
}

type ExtraAction = {
  key: string
  label: string
  variant?: 'ghost' | 'destructive'
  icon?: ReactNode
  onSelect: () => void
}

type MemberRoleActionsProps = {
  memberName: string
  memberEmail: string
  editRoleLabel: string
  roleLabel?: string
  roles: MemberRoleOption[]
  selectedRoleId?: string
  onSaveRole: (roleId: string) => void
  onRemoveRole?: () => void
  removeRoleLabel?: string
  onAddRole?: (selectRole: (roleId: string) => void) => void
  addRoleLabel?: string
  renderEffectivePreview?: (roleId: string) => ReactNode
  extraActions?: ExtraAction[]
}

function RoleActionButton({
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

export function MemberRoleActions({
  memberName,
  memberEmail,
  editRoleLabel,
  roleLabel = 'Role',
  roles,
  selectedRoleId,
  onSaveRole,
  onRemoveRole,
  removeRoleLabel = 'Remove role',
  onAddRole,
  addRoleLabel = 'New role',
  renderEffectivePreview,
  extraActions = [],
}: MemberRoleActionsProps) {
  const triggerRef = useRef<HTMLButtonElement>(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const [roleModalOpen, setRoleModalOpen] = useState(false)
  const [pendingRoleId, setPendingRoleId] = useState('')
  const iconProps = { size: 15, strokeWidth: 2 }

  const openRoleModal = () => {
    setPendingRoleId(selectedRoleId ?? roles[0]?.id ?? '')
    setRoleModalOpen(true)
    setMenuOpen(false)
  }

  const closeRoleModal = () => setRoleModalOpen(false)

  const saveRole = () => {
    if (!pendingRoleId) return
    onSaveRole(pendingRoleId)
    closeRoleModal()
  }

  const removeRole = () => {
    onRemoveRole?.()
    closeRoleModal()
  }

  const sections = [
    {
      actions: [
        {
          key: 'member',
          closeOnSelect: false,
          content: (
            <div className="flex w-full min-w-0 flex-col gap-1 rounded-sm px-3 py-2">
              <span className="truncate text-sm font-semibold text-foreground">{memberName}</span>
              <span className="truncate text-xs text-muted-foreground">{memberEmail}</span>
            </div>
          ),
        },
      ],
    },
    {
      actions: [
        {
          key: 'edit-role',
          content: (
            <RoleActionButton icon={<UserCog {...iconProps} />}>
              {editRoleLabel}
            </RoleActionButton>
          ),
          onSelect: openRoleModal,
        },
        ...extraActions.map((action) => ({
          key: action.key,
          content: (
            <RoleActionButton
              variant={action.variant}
              icon={action.icon ?? <Trash2 {...iconProps} />}
            >
              {action.label}
            </RoleActionButton>
          ),
          onSelect: action.onSelect,
        })),
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
        aria-expanded={menuOpen}
        aria-label={`Actions for ${memberName}`}
        onClick={() => setMenuOpen((open) => !open)}
      />
      <DropdownMenu
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        trigger={triggerRef}
        width="14rem"
        align="right"
        direction="auto"
        fullscreenAt="never"
        sections={sections}
      />
      <Modal
        open={roleModalOpen}
        onClose={closeRoleModal}
        title={editRoleLabel}
        width={520}
        footer={(
          <>
            <Button variant="secondary" onClick={closeRoleModal} className="mr-auto">Cancel</Button>
            {onRemoveRole && (
              <Button variant="destructive" onClick={removeRole}>{removeRoleLabel}</Button>
            )}
            <Button variant="primary" onClick={saveRole} disabled={!pendingRoleId}>Save</Button>
          </>
        )}
      >
        <div className="grid gap-4">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-foreground">{memberName}</p>
            <p className="truncate text-xs text-muted-foreground">{memberEmail}</p>
          </div>
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <Select
                label={roleLabel}
                value={pendingRoleId}
                onChange={(event) => setPendingRoleId(event.target.value)}
                options={roles.map((role) => ({ value: role.id, label: role.name }))}
              />
            </div>
            {onAddRole && (
              <Button
                variant="secondary"
                size="md"
                onClick={() => onAddRole(setPendingRoleId)}
              >
                {addRoleLabel}
              </Button>
            )}
          </div>
          {renderEffectivePreview && pendingRoleId && (
            <div className="grid gap-2 rounded-sm border border-border bg-muted/20 p-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Effective permissions
                </p>
                <Badge variant="muted" size="xxs">
                  Preview
                </Badge>
              </div>
              {renderEffectivePreview(pendingRoleId)}
            </div>
          )}
        </div>
      </Modal>
    </>
  )
}
