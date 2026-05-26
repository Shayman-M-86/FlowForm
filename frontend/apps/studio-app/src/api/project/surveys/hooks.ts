import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isDesignPreviewMode } from '../../designPreview'
import { getMockSurvey } from '../../mockData'
import { useOpenApiClient } from '../../openapi'
import { loadCachedQuery, loadCachedQueryUpdatedAt, saveCachedQuery } from '../../queryStorage'
import { projectKeys } from '../projects/hooks'
import { createSurvey, deleteSurvey, getSurvey, getSurveys, updateSurvey } from './requests'
import type { CreateSurveyRequest, SurveyOut, UpdateSurveyRequest } from './types'

const FIVE_MINUTES = 5 * 60 * 1000

export const surveyKeys = {
  all: () => ['surveys'] as const,
  list: (projectId: number) => [...surveyKeys.all(), 'list', projectId] as const,
  detail: (projectRef: string | number | null, surveyRef: string | number | null) =>
    [...surveyKeys.all(), 'detail', projectRef, surveyRef] as const,
}

export function useSurveys(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryKey = surveyKeys.list(projectId)

  return useQuery({
    queryKey,
    queryFn: async () => {
      const surveys = await getSurveys(apiClient, projectId)
      saveCachedQuery(queryKey, surveys)
      return surveys
    },
    enabled: projectId > 0,
    staleTime: FIVE_MINUTES,
    initialData: projectId > 0 ? loadCachedQuery<SurveyOut[]>(queryKey, FIVE_MINUTES) : undefined,
    initialDataUpdatedAt: () => projectId > 0 ? loadCachedQueryUpdatedAt(queryKey) : undefined,
  })
}

export function useSurvey(projectRef: string | number | null, surveyRef: string | number | null) {
  const apiClient = useOpenApiClient()
  const queryKey = surveyKeys.detail(projectRef, surveyRef)

  return useQuery({
    queryKey,
    queryFn: async () => {
      if (projectRef === null || surveyRef === null) throw new Error('refs are required')
      if (isDesignPreviewMode) {
        const mock = getMockSurvey(String(projectRef), String(surveyRef))
        return Promise.resolve(mock ? ({ title: mock.title } as SurveyOut) : null)
      }
      const survey = await getSurvey(apiClient, projectRef, surveyRef)
      saveCachedQuery(queryKey, survey)
      return survey
    },
    enabled: projectRef !== null && surveyRef !== null,
    staleTime: FIVE_MINUTES,
    initialData: projectRef !== null && surveyRef !== null && !isDesignPreviewMode
      ? loadCachedQuery<SurveyOut>(queryKey, FIVE_MINUTES)
      : undefined,
    initialDataUpdatedAt: () => projectRef !== null && surveyRef !== null && !isDesignPreviewMode
      ? loadCachedQueryUpdatedAt(queryKey)
      : undefined,
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
      const detailKey = surveyKeys.detail(projectRef, surveyRef)
      queryClient.setQueryData(detailKey, survey)
      saveCachedQuery(detailKey, survey)
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
