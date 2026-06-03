import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { STALE } from '@/lib/query/queryClient'
import type { components } from '@/api/generated/schema'

export type ProjectRoleOut = components['schemas']['ProjectRoleResponses']

const roleKeys = {
  list: (projectId: number) => ['roles', 'project', projectId] as const,
}

export function useProjectRoles(projectId: number | null) {
  return useQuery({
    queryKey: roleKeys.list(projectId ?? 0),
    enabled: projectId != null && projectId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/roles', {
        params: { path: { project_id: projectId! } },
      })
      if (error) throw error
      return data
    },
    staleTime: STALE.SLOW,
  })
}

export function useCreateProjectRole(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: components['schemas']['CreateProjectRoleRequest']) => {
      const { data, error } = await apiClient.POST('/api/v1/projects/{project_id}/roles', {
        params: { path: { project_id: projectId } },
        body,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: roleKeys.list(projectId) })
    },
  })
}

export function useUpdateProjectRole(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ roleId, body }: { roleId: number; body: components['schemas']['UpdateProjectRoleRequest'] }) => {
      const { data, error } = await apiClient.PATCH('/api/v1/projects/{project_id}/roles/{role_id}', {
        params: { path: { project_id: projectId, role_id: roleId } },
        body,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: roleKeys.list(projectId) })
    },
  })
}

export function useDeleteProjectRole(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (roleId: number) => {
      const { error } = await apiClient.DELETE('/api/v1/projects/{project_id}/roles/{role_id}', {
        params: { path: { project_id: projectId, role_id: roleId } },
      })
      if (error) throw error
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: roleKeys.list(projectId) })
    },
  })
}
