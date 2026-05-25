import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOpenApiClient } from '../../openapi'
import {
  createProjectRole,
  deleteProjectRole,
  getProjectRoles,
  updateProjectRole,
} from './requests'
import type { CreateProjectRoleRequest, ProjectRoleOut, UpdateProjectRoleRequest } from './types'

export const roleKeys = {
  all: () => ['roles'] as const,
  list: (projectId: number | null) => [...roleKeys.all(), 'list', projectId] as const,
}

export function useProjectRoles(projectId: number | null) {
  const apiClient = useOpenApiClient()

  return useQuery({
    queryKey: roleKeys.list(projectId),
    queryFn: () => {
      if (projectId === null) throw new Error('Project id is required')
      return getProjectRoles(apiClient, projectId)
    },
    enabled: projectId !== null,
  })
}

export function useCreateProjectRole(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: CreateProjectRoleRequest) => createProjectRole(apiClient, projectId, body),
    onSuccess: (role) => {
      queryClient.setQueryData<ProjectRoleOut[]>(roleKeys.list(projectId), (current) =>
        current ? [...current, role] : [role],
      )
    },
  })
}

export function useUpdateProjectRole(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ roleId, body }: { roleId: number; body: UpdateProjectRoleRequest }) =>
      updateProjectRole(apiClient, projectId, roleId, body),
    onSuccess: (updated) => {
      queryClient.setQueryData<ProjectRoleOut[]>(roleKeys.list(projectId), (current) =>
        current?.map((r) => (r.id === updated.id ? updated : r)),
      )
    },
  })
}

export function useDeleteProjectRole(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (roleId: number) => deleteProjectRole(apiClient, projectId, roleId),
    onSuccess: (_result, roleId) => {
      queryClient.setQueryData<ProjectRoleOut[]>(roleKeys.list(projectId), (current) =>
        current?.filter((r) => r.id !== roleId),
      )
    },
  })
}
