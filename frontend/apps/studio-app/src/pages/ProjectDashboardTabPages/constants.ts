import type { PermissionKey, PresetRoleDef } from './types'

export const CARD_WIDTH = 220
export const CARD_GAP = 16

export const ALL_PERMISSIONS: PermissionKey[] = [
  'project:edit',
  'project:delete',
  'project:manage_members',
  'project:manage_roles',
  'survey:view',
  'survey:create',
  'survey:edit',
  'survey:delete',
  'survey:publish',
  'survey:archive',
  'submission:view',
]

export const PERMISSION_GROUPS: { label: string; permissions: PermissionKey[] }[] = [
  {
    label: 'Project',
    permissions: [
      'project:edit',
      'project:delete',
      'project:manage_members',
      'project:manage_roles',
    ],
  },
  {
    label: 'Survey',
    permissions: [
      'survey:view',
      'survey:create',
      'survey:edit',
      'survey:delete',
      'survey:publish',
      'survey:archive',
    ],
  },
  {
    label: 'Submissions',
    permissions: ['submission:view'],
  },
]

export const PERMISSION_LABEL: Record<PermissionKey, string> = {
  'project:edit': 'Edit project',
  'project:delete': 'Delete project',
  'project:manage_members': 'Manage members',
  'project:manage_roles': 'Manage roles',
  'survey:view': 'View surveys',
  'survey:create': 'Create surveys',
  'survey:edit': 'Edit surveys',
  'survey:delete': 'Delete surveys',
  'survey:publish': 'Publish surveys',
  'survey:archive': 'Archive surveys',
  'submission:view': 'View submissions',
}

export const PRESET_ROLES: PresetRoleDef[] = [
  {
    id: 'admin',
    name: 'Admin',
    description: 'Full access to everything in this project.',
    permissions: [...ALL_PERMISSIONS],
  },
  {
    id: 'contributor',
    name: 'Contributor',
    description: 'Full survey and submission access. No project management.',
    permissions: [
      'survey:view',
      'survey:create',
      'survey:edit',
      'survey:delete',
      'survey:publish',
      'survey:archive',
      'submission:view',
    ],
  },
  {
    id: 'analyst',
    name: 'Analyst',
    description: 'Read-only access to surveys and submissions.',
    permissions: ['survey:view', 'submission:view'],
  },
]
