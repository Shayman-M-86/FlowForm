import { Badge, Button } from '@flowform/ui'
import { PRESET_ROLES } from './constants'
import type { CustomRole } from './types'

interface ManagementTabProps {
  customRoles: CustomRole[]
  onAddRole: () => void
}

export function ManagementTab({ customRoles, onAddRole }: ManagementTabProps) {
  const allRoleCount = PRESET_ROLES.length + customRoles.length

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">{allRoleCount} roles</p>
        <Button variant="secondary" size="sm" onClick={onAddRole}>
          Add role
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        {PRESET_ROLES.map((role) => (
          <Badge key={role.id} variant="muted" size="xs">{role.name}</Badge>
        ))}
        {customRoles.map((role) => (
          <Badge key={role.id} variant="accent" size="xs">{role.name}</Badge>
        ))}
      </div>
    </div>
  )
}
