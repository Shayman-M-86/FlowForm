import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOpenApiClient } from '../../openapi'
import { loadCachedQuery, loadCachedQueryUpdatedAt, saveCachedQuery } from '../../queryStorage'
import {
  assignSurveyMemberRole,
  getSurveyMembers,
  removeSurveyMemberRole,
  updateSurveyMemberRole,
} from './requests'
import type { AssignSurveyMemberRoleRequest, SurveyMemberRoleOut, UpdateSurveyMemberRoleRequest } from './types'

const ONE_MINUTE = 60 * 1000

export const surveyMemberKeys = {
  all: () => ['survey-members'] as const,
  list: (projectId: number, surveyId: number) =>
    [...surveyMemberKeys.all(), 'list', projectId, surveyId] as const,
}

export function useSurveyMembers(projectId: number, surveyId: number) {
  const apiClient = useOpenApiClient()
  const queryKey = surveyMemberKeys.list(projectId, surveyId)

  return useQuery({
    queryKey,
    queryFn: async () => {
      const members = await getSurveyMembers(apiClient, projectId, surveyId)
      saveCachedQuery(queryKey, members)
      return members
    },
    enabled: projectId > 0 && surveyId > 0,
    staleTime: ONE_MINUTE,
    initialData: projectId > 0 && surveyId > 0
      ? loadCachedQuery<SurveyMemberRoleOut[]>(queryKey, ONE_MINUTE)
      : undefined,
    initialDataUpdatedAt: () => projectId > 0 && surveyId > 0 ? loadCachedQueryUpdatedAt(queryKey) : undefined,
  })
}

export function useAssignSurveyMemberRole(projectId: number, surveyId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: AssignSurveyMemberRoleRequest) =>
      assignSurveyMemberRole(apiClient, projectId, surveyId, body),
    onSuccess: (assignment) => {
      const queryKey = surveyMemberKeys.list(projectId, surveyId)
      queryClient.setQueryData<SurveyMemberRoleOut[]>(queryKey, (current) => {
        const next = current ? [...current, assignment] : [assignment]
        saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}

export function useUpdateSurveyMemberRole(projectId: number, surveyId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ membershipId, body }: { membershipId: number; body: UpdateSurveyMemberRoleRequest }) =>
      updateSurveyMemberRole(apiClient, projectId, surveyId, membershipId, body),
    onSuccess: (updated) => {
      const queryKey = surveyMemberKeys.list(projectId, surveyId)
      queryClient.setQueryData<SurveyMemberRoleOut[]>(queryKey, (current) => {
        const next = current?.map((a) => (a.membership_id === updated.membership_id ? updated : a))
        if (next) saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}

export function useRemoveSurveyMemberRole(projectId: number, surveyId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (membershipId: number) =>
      removeSurveyMemberRole(apiClient, projectId, surveyId, membershipId),
    onSuccess: (_result, membershipId) => {
      const queryKey = surveyMemberKeys.list(projectId, surveyId)
      queryClient.setQueryData<SurveyMemberRoleOut[]>(queryKey, (current) => {
        const next = current?.filter((a) => a.membership_id !== membershipId)
        if (next) saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}
