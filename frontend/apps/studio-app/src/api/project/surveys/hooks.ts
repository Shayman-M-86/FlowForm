import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isDesignPreviewMode } from '../../designPreview'
import { getMockSurvey } from '../../mockData'
import { useOpenApiClient } from '../../openapi'
import { projectKeys } from '../projects/hooks'
import { createSurvey, deleteSurvey, getSurvey, getSurveys, updateSurvey } from './requests'
import type { CreateSurveyRequest, SurveyOut, UpdateSurveyRequest } from './types'

export const surveyKeys = {
  all: () => ['surveys'] as const,
  list: (projectId: number) => [...surveyKeys.all(), 'list', projectId] as const,
  detail: (projectRef: string | number | null, surveyRef: string | number | null) =>
    [...surveyKeys.all(), 'detail', projectRef, surveyRef] as const,
}

export function useSurveys(projectId: number) {
  const apiClient = useOpenApiClient()

  return useQuery({
    queryKey: surveyKeys.list(projectId),
    queryFn: () => getSurveys(apiClient, projectId),
  })
}

export function useSurvey(projectRef: string | null, surveyRef: string | null) {
  const apiClient = useOpenApiClient()

  return useQuery({
    queryKey: surveyKeys.detail(projectRef, surveyRef),
    queryFn: () => {
      if (projectRef === null || surveyRef === null) throw new Error('refs are required')
      if (isDesignPreviewMode) {
        const mock = getMockSurvey(projectRef, surveyRef)
        return Promise.resolve(mock ? ({ title: mock.title } as SurveyOut) : null)
      }
      return getSurvey(apiClient, projectRef, surveyRef)
    },
    enabled: projectRef !== null && surveyRef !== null,
  })
}

export function useCreateSurvey(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: CreateSurveyRequest) => createSurvey(apiClient, projectId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyKeys.list(projectId) })
    },
  })
}

export function useUpdateSurvey(projectRef: string | number, surveyRef: string | number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: UpdateSurveyRequest) => updateSurvey(apiClient, projectRef, surveyRef, body),
    onSuccess: (survey) => {
      queryClient.setQueryData(surveyKeys.detail(projectRef, surveyRef), survey)
      void queryClient.invalidateQueries({ queryKey: surveyKeys.list(survey.project_id) })
    },
  })
}

export function useDeleteSurvey(projectRef: string | number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (surveyRef: string | number) => deleteSurvey(apiClient, projectRef, surveyRef),
    onSuccess: (_result, surveyRef) => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all() })
      void queryClient.invalidateQueries({ queryKey: surveyKeys.detail(projectRef, surveyRef) })
    },
  })
}
