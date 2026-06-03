import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { usePolicyQuery } from '@/lib/query/usePolicyQuery'
import { QUERY_POLICIES } from '@/lib/query/queryPolicy'
import type { components } from '@/api/generated/schema'

export type SurveyRoleOut = components['schemas']['SurveyRoleResponses']
export type CreateSurveyRoleRequest = components['schemas']['CreateSurveyRoleRequest']
export type UpdateSurveyRoleRequest = components['schemas']['UpdateSurveyRoleRequest']

const surveyRoleKeys = {
  list: (projectId: number) => ['survey-roles', 'project', projectId] as const,
}

export function useSurveyRoles(projectId: number | null) {
  return usePolicyQuery({
    queryKey: surveyRoleKeys.list(projectId ?? 0),
    enabled: projectId != null && projectId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/survey-roles', {
        params: { path: { project_id: projectId! } },
      })
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.surveyRoles,
  })
}

export function useCreateSurveyRole(projectId: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: components['schemas']['CreateSurveyRoleRequest']) => {
      if (projectId == null) throw new Error('projectId is required')
      const { data, error } = await apiClient.POST('/api/v1/projects/{project_id}/survey-roles', {
        params: { path: { project_id: projectId } },
        body,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      if (projectId != null) {
        void queryClient.invalidateQueries({ queryKey: surveyRoleKeys.list(projectId) })
      }
    },
  })
}

export function useUpdateSurveyRole(projectId: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ roleId, body }: { roleId: number; body: components['schemas']['UpdateSurveyRoleRequest'] }) => {
      if (projectId == null) throw new Error('projectId is required')
      const { data, error } = await apiClient.PATCH(
        '/api/v1/projects/{project_id}/survey-roles/{role_id}',
        { params: { path: { project_id: projectId, role_id: roleId } }, body },
      )
      if (error) throw error
      return data
    },
    onSuccess: () => {
      if (projectId != null) {
        void queryClient.invalidateQueries({ queryKey: surveyRoleKeys.list(projectId) })
      }
    },
  })
}

export function useDeleteSurveyRole(projectId: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (roleId: number) => {
      if (projectId == null) throw new Error('projectId is required')
      const { error } = await apiClient.DELETE(
        '/api/v1/projects/{project_id}/survey-roles/{role_id}',
        { params: { path: { project_id: projectId, role_id: roleId } } },
      )
      if (error) throw error
    },
    onSuccess: () => {
      if (projectId != null) {
        void queryClient.invalidateQueries({ queryKey: surveyRoleKeys.list(projectId) })
      }
    },
  })
}
