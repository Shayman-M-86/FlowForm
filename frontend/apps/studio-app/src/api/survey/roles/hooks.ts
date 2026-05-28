import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOpenApiClient } from '../../openapi'
import { loadCachedQuery, loadCachedQueryUpdatedAt, saveCachedQuery } from '../../queryStorage'
import { createSurveyRole, deleteSurveyRole, getSurveyRoles, updateSurveyRole } from './requests'
import type { CreateSurveyRoleRequest, SurveyRoleOut, UpdateSurveyRoleRequest } from './types'

const FIVE_MINUTES = 5 * 60 * 1000

export const surveyRoleKeys = {
  all: () => ['survey-roles'] as const,
  list: (projectId: number) => [...surveyRoleKeys.all(), 'list', projectId] as const,
}

export function useSurveyRoles(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryKey = surveyRoleKeys.list(projectId)

  return useQuery({
    queryKey,
    queryFn: async () => {
      const roles = await getSurveyRoles(apiClient, projectId)
      saveCachedQuery(queryKey, roles)
      return roles
    },
    enabled: projectId > 0,
    staleTime: FIVE_MINUTES,
    initialData: projectId > 0 ? loadCachedQuery<SurveyRoleOut[]>(queryKey, FIVE_MINUTES) : undefined,
    initialDataUpdatedAt: () => projectId > 0 ? loadCachedQueryUpdatedAt(queryKey) : undefined,
  })
}

export function useCreateSurveyRole(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: CreateSurveyRoleRequest) => createSurveyRole(apiClient, projectId, body),
    onSuccess: (role) => {
      const queryKey = surveyRoleKeys.list(projectId)
      queryClient.setQueryData<SurveyRoleOut[]>(queryKey, (current) => {
        const next = current ? [...current, role] : [role]
        saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}

export function useUpdateSurveyRole(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ roleId, body }: { roleId: number; body: UpdateSurveyRoleRequest }) =>
      updateSurveyRole(apiClient, projectId, roleId, body),
    onSuccess: (updated) => {
      const queryKey = surveyRoleKeys.list(projectId)
      queryClient.setQueryData<SurveyRoleOut[]>(queryKey, (current) => {
        const next = current?.map((r) => (r.id === updated.id ? updated : r))
        if (next) saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}

export function useDeleteSurveyRole(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (roleId: number) => deleteSurveyRole(apiClient, projectId, roleId),
    onSuccess: (_result, roleId) => {
      const queryKey = surveyRoleKeys.list(projectId)
      queryClient.setQueryData<SurveyRoleOut[]>(queryKey, (current) => {
        const next = current?.filter((r) => r.id !== roleId)
        if (next) saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}
