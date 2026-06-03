import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { STALE } from '@/lib/query/queryClient'
import type { components } from '@/api/generated/schema'

export type SurveyVersionOut = components['schemas']['SurveyVersionResponses']

const versionKeys = {
  list: (projectId: number, surveyId: number) =>
    ['versions', 'project', projectId, 'survey', surveyId] as const,
}

export function useSurveyVersions(projectId: number, surveyId: number) {
  return useQuery({
    queryKey: versionKeys.list(projectId, surveyId),
    enabled: projectId > 0 && surveyId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/versions',
        { params: { path: { project_id: projectId, survey_id: surveyId } } },
      )
      if (error) throw error
      return data
    },
    staleTime: STALE.ACTIVE,
  })
}

export function useCreateSurveyVersion(projectId: number, surveyId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (_?: undefined) => {
      const { data, error } = await apiClient.POST(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/versions',
        { params: { path: { project_id: projectId, survey_id: surveyId } } },
      )
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: versionKeys.list(projectId, surveyId) })
    },
  })
}

export function usePublishSurveyVersion(projectId: number, surveyId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (versionNumber: number) => {
      const { data, error } = await apiClient.POST(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/publish',
        { params: { path: { project_id: projectId, survey_id: surveyId, version_number: versionNumber } } },
      )
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: versionKeys.list(projectId, surveyId) })
    },
  })
}

export function useArchiveSurveyVersion(projectId: number, surveyId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (versionNumber: number) => {
      const { data, error } = await apiClient.POST(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/archive',
        { params: { path: { project_id: projectId, survey_id: surveyId, version_number: versionNumber } } },
      )
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: versionKeys.list(projectId, surveyId) })
    },
  })
}

export function useCopyVersionToDraft(projectId: number, surveyId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (versionNumber: number) => {
      const { data, error } = await apiClient.POST(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/copy-to-draft',
        { params: { path: { project_id: projectId, survey_id: surveyId, version_number: versionNumber } } },
      )
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: versionKeys.list(projectId, surveyId) })
    },
  })
}
