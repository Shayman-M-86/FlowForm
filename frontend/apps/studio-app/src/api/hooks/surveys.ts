import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { STALE } from '@/lib/query/queryClient'
import type { components } from '@/api/generated/schema'
import { useProject } from '@/api/hooks/projects'

export type SurveyOut = components['schemas']['SurveyResponses']

const surveyKeys = {
  list: (projectId: number) => ['surveys', 'project', projectId] as const,
  detail: (projectId: number, surveyId: number) => ['surveys', 'project', projectId, 'id', surveyId] as const,
}

export function useSurveys(projectId: number) {
  return useQuery({
    queryKey: surveyKeys.list(projectId),
    enabled: projectId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/surveys', {
        params: { path: { project_id: projectId } },
      })
      if (error) throw error
      return data
    },
    staleTime: STALE.SLOW,
  })
}

// surveySlug is always a numeric string from the route (e.g. "42") — not a semantic slug.
export function useSurvey(projectSlug: string | null, surveySlug: string | null) {
  const { data: project } = useProject(projectSlug)
  const projectId = project?.id ?? null
  const surveyId = surveySlug != null ? Number(surveySlug) : NaN

  return useQuery({
    queryKey: projectId != null && Number.isInteger(surveyId) && surveyId > 0
      ? surveyKeys.detail(projectId, surveyId)
      : ['surveys', 'disabled'],
    enabled: projectId != null && Number.isInteger(surveyId) && surveyId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        '/api/v1/projects/{project_id}/surveys/{survey_id}',
        { params: { path: { project_id: projectId!, survey_id: surveyId } } },
      )
      if (error) throw error
      return data
    },
    staleTime: STALE.SLOW,
  })
}

export function useUpdateSurvey(projectId: number | null, surveySlug: string | null) {
  const queryClient = useQueryClient()
  const surveyId = surveySlug != null ? Number(surveySlug) : NaN

  return useMutation({
    mutationFn: async (body: components['schemas']['UpdateSurveyRequest']) => {
      if (projectId == null || !Number.isInteger(surveyId) || surveyId <= 0) {
        throw new Error('projectId and surveyId are required')
      }
      const { data, error } = await apiClient.PATCH(
        '/api/v1/projects/{project_id}/surveys/{survey_id}',
        { params: { path: { project_id: projectId, survey_id: surveyId } }, body },
      )
      if (error) throw error
      return data
    },
    onSuccess: () => {
      if (projectId != null && Number.isInteger(surveyId) && surveyId > 0) {
        void queryClient.invalidateQueries({ queryKey: surveyKeys.list(projectId) })
        void queryClient.invalidateQueries({ queryKey: surveyKeys.detail(projectId, surveyId) })
      }
    },
  })
}

export function useCreateSurvey(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: components['schemas']['CreateSurveyRequest']) => {
      const { data, error } = await apiClient.POST('/api/v1/projects/{project_id}/surveys', {
        params: { path: { project_id: projectId } },
        body,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyKeys.list(projectId) })
    },
  })
}

export function useDeleteSurvey(projectId: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (surveyId: number) => {
      if (projectId == null) throw new Error('projectId is required')
      const { error } = await apiClient.DELETE('/api/v1/projects/{project_id}/surveys/{survey_id}', {
        params: { path: { project_id: projectId, survey_id: surveyId } },
      })
      if (error) throw error
    },
    onSuccess: (_, surveyId) => {
      if (projectId != null) {
        void queryClient.invalidateQueries({ queryKey: surveyKeys.list(projectId) })
        queryClient.removeQueries({ queryKey: surveyKeys.detail(projectId, surveyId) })
      }
    },
  })
}
