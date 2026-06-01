import { useParams } from '@tanstack/react-router'
import { Card, Spinner } from '@flowform/ui'
import { RolesWorkspace } from './RolesWorkspace'
import {
  PROJECT_PERMISSION_GROUPS,
  PRESET_ROLES,
} from './roleDefinitions'
import {
  useCreateProjectRole,
  useDeleteProjectRole,
  useProjectRoles,
  useUpdateProjectRole,
} from '@/api/hooks/roles'
import { useProject } from '@/api/hooks/projects'
import { useHasProjectPermission } from '@/api/hooks/permissions'

export {
  PERMISSION_LABEL,
  PERMISSION_TOOLTIP,
  PROJECT_PERMISSION_GROUPS as PERMISSION_GROUPS,
  PRESET_ROLES,
} from './roleDefinitions'

export type { CustomRole, PermissionGroup, PermissionKey } from './roleDefinitions'

import { useRenderDebug } from '@/debug/useRenderDebug'

function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message
  if (typeof error === 'object' && error && 'message' in error && typeof error.message === 'string') return error.message
  return 'Project roles could not be loaded.'
}

export function RolesTab() {
  useRenderDebug('RolesTab')
  const { slug } = useParams({ strict: false })
  const projectQuery = useProject(slug ?? null)
  const projectId = projectQuery.data?.id ?? null
  const canManageRoles = useHasProjectPermission(projectId, 'project:manage_roles')
  const { data: roles = [], isLoading, isError, error } = useProjectRoles(projectId)
  const mutationProjectId = projectId ?? 0
  const createRole = useCreateProjectRole(mutationProjectId)
  const updateRole = useUpdateProjectRole(mutationProjectId)
  const deleteRole = useDeleteProjectRole(mutationProjectId)

  if (projectQuery.isLoading || isLoading) {
    return (
      <div className="flex justify-center py-10">
        <Spinner size={24} />
      </div>
    )
  }

  if (projectQuery.isError || isError) {
    return (
      <Card tone="muted">
        <p className="text-sm text-destructive">{getErrorMessage(projectQuery.error ?? error)}</p>
      </Card>
    )
  }

  if (projectId === null) return null

  return (
    <RolesWorkspace
      presets={PRESET_ROLES}
      permissionGroups={PROJECT_PERMISSION_GROUPS}
      persistedRoles={roles}
      onCreateRole={async (role) => {
        await createRole.mutateAsync({ name: role.name, description: role.description, permissions: role.permissions })
      }}
      onUpdateRole={async (roleId, role) => {
        await updateRole.mutateAsync({
          roleId,
          body: { name: role.name, description: role.description, permissions: role.permissions },
        })
      }}
      onDeleteRole={async (roleId) => {
        await deleteRole.mutateAsync(roleId)
      }}
      isSaving={createRole.isPending || updateRole.isPending}
      isDeleting={deleteRole.isPending}
      defaultRoleDescription="Custom project role."
      readOnly={!canManageRoles}
    />
  )
}
