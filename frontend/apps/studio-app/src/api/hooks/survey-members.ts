import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { usePolicyQuery } from '@/lib/query/usePolicyQuery'
import { QUERY_POLICIES } from '@/lib/query/queryPolicy'
import type { components } from '@/api/generated/schema'

export type SurveyMemberRoleOut = components['schemas']['SurveyMemberRoleResponses']

const surveyMemberKeys = {
  list: (projectId: number, surveyId: number) =>
    ['survey-members', 'project', projectId, 'survey', surveyId] as const,
}

export function useSurveyMembers(projectId: number | null, surveyId: number | null) {
  return usePolicyQuery({
    queryKey: surveyMemberKeys.list(projectId ?? 0, surveyId ?? 0),
    enabled: projectId != null && projectId > 0 && surveyId != null && surveyId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/members',
        { params: { path: { project_id: projectId!, survey_id: surveyId! } } },
      )
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.surveyMembers,
  })
}

export function useAssignSurveyMemberRole(projectId: number | null, surveyId: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: components['schemas']['AssignSurveyMemberRoleRequest']) => {
      if (projectId == null || surveyId == null) throw new Error('projectId and surveyId are required')
      const { data, error } = await apiClient.POST(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/members',
        { params: { path: { project_id: projectId, survey_id: surveyId } }, body },
      )
      if (error) throw error
      return data
    },
    onSuccess: () => {
      if (projectId != null && surveyId != null) {
        void queryClient.invalidateQueries({ queryKey: surveyMemberKeys.list(projectId, surveyId) })
      }
    },
  })
}

export function useUpdateSurveyMemberRole(projectId: number | null, surveyId: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      membershipId,
      body,
    }: {
      membershipId: number
      body: components['schemas']['UpdateSurveyMemberRoleRequest']
    }) => {
      if (projectId == null || surveyId == null) throw new Error('projectId and surveyId are required')
      const { data, error } = await apiClient.PATCH(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/members/{membership_id}',
        { params: { path: { project_id: projectId, survey_id: surveyId, membership_id: membershipId } }, body },
      )
      if (error) throw error
      return data
    },
    onSuccess: () => {
      if (projectId != null && surveyId != null) {
        void queryClient.invalidateQueries({ queryKey: surveyMemberKeys.list(projectId, surveyId) })
      }
    },
  })
}

export function useRemoveSurveyMemberRole(projectId: number | null, surveyId: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (membershipId: number) => {
      if (projectId == null || surveyId == null) throw new Error('projectId and surveyId are required')
      const { error } = await apiClient.DELETE(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/members/{membership_id}',
        { params: { path: { project_id: projectId, survey_id: surveyId, membership_id: membershipId } } },
      )
      if (error) throw error
    },
    onSuccess: () => {
      if (projectId != null && surveyId != null) {
        void queryClient.invalidateQueries({ queryKey: surveyMemberKeys.list(projectId, surveyId) })
      }
    },
  })
}
