import { RolesWorkspace } from './RolesWorkspace'
import {
  PROJECT_PERMISSION_GROUPS,
  PRESET_ROLES,
} from './roleDefinitions'

export {
  PERMISSION_LABEL,
  PERMISSION_TOOLTIP,
  PROJECT_PERMISSION_GROUPS as PERMISSION_GROUPS,
  PRESET_ROLES,
} from './roleDefinitions'

export type { CustomRole, PermissionGroup, PermissionKey } from './roleDefinitions'

import { useRenderDebug } from '@/debug/useRenderDebug'

export function RolesTab() {
  useRenderDebug('RolesTab')
  return (
    <RolesWorkspace
      presets={PRESET_ROLES}
      permissionGroups={PROJECT_PERMISSION_GROUPS}
      defaultRoleDescription="Custom project role."
    />
  )
}
