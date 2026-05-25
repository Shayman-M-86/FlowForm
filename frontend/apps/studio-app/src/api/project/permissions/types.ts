import type { MyProjectPermissionsOut } from '../../generated/schema'

export type { MyProjectPermissionsOut }

export type ProjectPermission = MyProjectPermissionsOut['permissions'][number]

export const PERMISSION_REQUIRED_TOOLTIP: Record<string, string> = {
  surveys:  'Requires Permission: survey:view',
  members:  'Requires Permission: project:manage_members',
  roles:    'Requires Permission: project:manage_roles',
  settings: 'Requires Permission: project:edit or project:delete',
}
