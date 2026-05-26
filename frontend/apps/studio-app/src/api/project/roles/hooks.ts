import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOpenApiClient } from '../../openapi'
import { loadCachedQuery, loadCachedQueryUpdatedAt, saveCachedQuery } from '../../queryStorage'
import {
  createProjectRole,
  deleteProjectRole,
  getProjectRoles,
  updateProjectRole,
} from './requests'
import type { CreateProjectRoleRequest, ProjectRoleOut, UpdateProjectRoleRequest } from './types'

const FIVE_MINUTES = 5 * 60 * 1000

export const roleKeys = {
  all: () => ['roles'] as const,
  list: (projectId: number | null) => [...roleKeys.all(), 'list', projectId] as const,
}

export function useProjectRoles(projectId: number | null) {
  const apiClient = useOpenApiClient()
  const queryKey = roleKeys.list(projectId)

  return useQuery({
    queryKey,
    queryFn: async () => {
      if (projectId === null) throw new Error('Project id is required')
      const roles = await getProjectRoles(apiClient, projectId)
      saveCachedQuery(queryKey, roles)
      return roles
    },
    enabled: projectId !== null && projectId > 0,
    staleTime: FIVE_MINUTES,
    initialData: projectId !== null && projectId > 0
      ? loadCachedQuery<ProjectRoleOut[]>(queryKey, FIVE_MINUTES)
      : undefined,
    initialDataUpdatedAt: () => projectId !== null && projectId > 0 ? loadCachedQueryUpdatedAt(queryKey) : undefined,
  })
}

export function useCreateProjectRole(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: CreateProjectRoleRequest) => createProjectRole(apiClient, projectId, body),
    onSuccess: (role) => {
      const queryKey = roleKeys.list(projectId)
      queryClient.setQueryData<ProjectRoleOut[]>(queryKey, (current) => {
        const next = current ? [...current, role] : [role]
        saveCachedQuery(queryKey, next)
        return next
      })
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
      const queryKey = roleKeys.list(projectId)
      queryClient.setQueryData<ProjectRoleOut[]>(queryKey, (current) => {
        const next = current?.map((r) => (r.id === updated.id ? updated : r))
        if (next) saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}

export function useDeleteProjectRole(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (roleId: number) => deleteProjectRole(apiClient, projectId, roleId),
    onSuccess: (_result, roleId) => {
      const queryKey = roleKeys.list(projectId)
      queryClient.setQueryData<ProjectRoleOut[]>(queryKey, (current) => {
        const next = current?.filter((r) => r.id !== roleId)
        if (next) saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}
