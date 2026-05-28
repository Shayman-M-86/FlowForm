import { Badge, Tooltip } from '@flowform/ui'
import {
  PERMISSION_LABEL,
  PERMISSION_TOOLTIP,
  type PermissionKey,
} from '@/pages/ProjectDashboardTabPages/roleDefinitions'

type BadgeVariant = 'default' | 'success' | 'danger' | 'warning' | 'accent' | 'muted'

type PermissionBadgeProps = {
  permission: PermissionKey
  variant?: BadgeVariant
}

export function PermissionBadge({ permission, variant = 'default' }: PermissionBadgeProps) {
  return (
    <Tooltip title={PERMISSION_TOOLTIP[permission]} size="md">
      <Badge variant={variant} size="xs">
        {PERMISSION_LABEL[permission]}
      </Badge>
    </Tooltip>
  )
}
