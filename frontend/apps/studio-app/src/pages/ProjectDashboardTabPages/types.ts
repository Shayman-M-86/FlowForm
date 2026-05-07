export type RoleFilter = 'all' | 'default' | 'custom'

export type SurveySummary = {
  id: number
  name: string
  status: 'Draft' | 'Published' | 'Paused'
  visibility: 'Private' | 'Link only' | 'Public'
  responses: number
  updatedAt: string
}

export type Member = {
  id: number
  name: string
  email: string
  role: 'Owner' | 'Editor' | 'Viewer'
}

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

export type RoleEditorState = {
  id: string
  custom: boolean
  name: string
  description: string
  permissions: Set<PermissionKey>
}

export type PresetRoleDef = {
  id: string
  name: string
  description: string
  permissions: PermissionKey[]
}
