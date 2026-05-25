export type PermissionKey =
  | 'project:edit'
  | 'project:delete'
  | 'project:manage_members'
  | 'project:manage_roles'
  | 'survey:view'
  | 'survey:create'
  | 'survey:edit'
  | 'survey:delete'
  | 'survey:publish'
  | 'survey:archive'
  | 'submission:view'

export type CustomRole = {
  id: string
  name: string
  description: string
  permissions: PermissionKey[]
}

export type PermissionGroup = { label: string; permissions: PermissionKey[] }

export type RolePreset = {
  id: string
  name: string
  description: string
  permissions: PermissionKey[]
}

export type ProjectMemberRoleLabel = 'Owner' | 'Editor' | 'Viewer'
export type RoleWithPermissions = RolePreset | CustomRole

const ALL_PROJECT_PERMISSIONS: PermissionKey[] = [
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

const PERMISSION_KEY_SET = new Set<string>(ALL_PROJECT_PERMISSIONS)

export function isPermissionKey(permission: string): permission is PermissionKey {
  return PERMISSION_KEY_SET.has(permission)
}

export function permissionKeyFromValue(value: unknown): PermissionKey | null {
  if (typeof value === 'string') return isPermissionKey(value) ? value : null
  if (!value || typeof value !== 'object') return null

  for (const field of ['name', 'key', 'permission']) {
    const permission = (value as Record<string, unknown>)[field]
    if (typeof permission === 'string' && isPermissionKey(permission)) return permission
  }

  return null
}

export function normalizePermissionKeys(values: readonly unknown[]): PermissionKey[] {
  const permissions = new Set<PermissionKey>()
  values.forEach((value) => {
    const permission = permissionKeyFromValue(value)
    if (permission) permissions.add(permission)
  })
  return [...permissions]
}

export const PROJECT_PERMISSION_GROUPS: PermissionGroup[] = [
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

export const SURVEY_PERMISSION_GROUPS: PermissionGroup[] = [
  {
    label: 'Survey',
    permissions: [
      'survey:view',
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

export const PERMISSION_TOOLTIP: Record<PermissionKey, string> = {
  'project:edit':
    'Allows changes to project-level details such as the project name, slug, and general configuration.',
  'project:delete':
    'Allows permanent removal of the project and its related workspace data. Reserve this for trusted administrators.',
  'project:manage_members':
    'Allows inviting, removing, and changing project members, including assigning roles to other people.',
  'project:manage_roles':
    'Allows creating and editing roles, including changing which permissions each role grants.',
  'survey:view':
    'Allows viewing surveys in the project, including draft and published survey structure.',
  'survey:create':
    'Allows creating new surveys and starting new survey drafts within this project.',
  'survey:edit':
    'Allows editing survey content, question order, branching logic, and survey settings.',
  'survey:delete':
    'Allows deleting surveys from the project. Use carefully when surveys may contain live work.',
  'survey:publish':
    'Allows publishing surveys, pausing live surveys, and changing whether respondents can access them.',
  'survey:archive':
    'Allows archiving surveys that should no longer appear in active project workflows.',
  'submission:view':
    'Allows viewing collected responses, submission summaries, and respondent data available to the project.',
}

export const PRESET_ROLES: RolePreset[] = [
  {
    id: 'admin',
    name: 'Admin',
    description: 'Full access to everything in this project.',
    permissions: [...ALL_PROJECT_PERMISSIONS],
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

export const DEFAULT_PROJECT_INVITE_ROLE_ID = 'analyst'

export const PROJECT_MEMBER_ROLE_TO_ROLE_ID: Record<ProjectMemberRoleLabel, string> = {
  Owner: 'admin',
  Editor: 'contributor',
  Viewer: 'analyst',
}

export const SURVEY_PRESET_ROLES: RolePreset[] = [
  {
    id: 'survey-manager',
    name: 'Manager',
    description: 'Can manage this survey, publish changes, and view responses.',
    permissions: ['survey:view', 'survey:edit', 'survey:delete', 'survey:publish', 'survey:archive', 'submission:view'],
  },
  {
    id: 'survey-publisher',
    name: 'Publisher',
    description: 'Can edit, publish, and view responses for this survey.',
    permissions: ['survey:view', 'survey:edit', 'survey:publish', 'submission:view'],
  },
  {
    id: 'survey-viewer',
    name: 'Viewer',
    description: 'Can view this survey and its available details.',
    permissions: ['survey:view'],
  },
]

export const PROJECT_ROLE_TO_SURVEY_ROLE_ID: Record<ProjectMemberRoleLabel, string> = {
  Owner: 'survey-manager',
  Editor: 'survey-viewer',
  Viewer: 'survey-viewer',
}

export const DEFAULT_SURVEY_ROLE_ASSIGNMENTS: Record<number, string> = {
  2: 'survey-manager',
  4: 'survey-viewer',
}

export function roleForId<TRole extends RoleWithPermissions>(
  roles: TRole[],
  roleId: string,
): TRole | undefined {
  return roles.find((role) => role.id === roleId)
}

export function rolePermissions(roles: RoleWithPermissions[], roleId: string): PermissionKey[] {
  return roleForId(roles, roleId)?.permissions ?? []
}

export function permissionsGained(
  roles: RoleWithPermissions[],
  baselineRoleId: string,
  roleId: string,
): PermissionKey[] {
  const baseline = new Set(rolePermissions(roles, baselineRoleId))
  return rolePermissions(roles, roleId).filter((permission) => !baseline.has(permission))
}
