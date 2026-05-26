import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOpenApiClient } from '../../openapi'
import { loadCachedQuery, loadCachedQueryUpdatedAt, saveCachedQuery } from '../../queryStorage'
import {
  archiveSurveyVersion,
  copyVersionToDraft,
  createSurveyVersion,
  getSurveyVersions,
  publishSurveyVersion,
} from './requests'
import type { SurveyVersionOut } from './types'

const ONE_MINUTE = 60 * 1000

export const surveyVersionKeys = {
  all: () => ['survey-versions'] as const,
  list: (projectId: number, surveyId: number) =>
    [...surveyVersionKeys.all(), 'list', projectId, surveyId] as const,
}

export function useSurveyVersions(projectId: number, surveyId: number) {
  const apiClient = useOpenApiClient()
  const queryKey = surveyVersionKeys.list(projectId, surveyId)

  return useQuery({
    queryKey,
    queryFn: async () => {
      const versions = await getSurveyVersions(apiClient, projectId, surveyId)
      saveCachedQuery(queryKey, versions)
      return versions
    },
    enabled: projectId > 0 && surveyId > 0,
    staleTime: ONE_MINUTE,
    initialData: projectId > 0 && surveyId > 0
      ? loadCachedQuery<SurveyVersionOut[]>(queryKey, ONE_MINUTE)
      : undefined,
    initialDataUpdatedAt: () => projectId > 0 && surveyId > 0 ? loadCachedQueryUpdatedAt(queryKey) : undefined,
  })
}

export function useCreateSurveyVersion(projectId: number, surveyId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => createSurveyVersion(apiClient, projectId, surveyId),
    onSuccess: (version) => {
      const queryKey = surveyVersionKeys.list(projectId, surveyId)
      queryClient.setQueryData<SurveyVersionOut[]>(queryKey, (current) => {
        const next = current ? [...current, version] : [version]
        saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}

export function useCopyVersionToDraft(projectId: number, surveyId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (versionNumber: number) => copyVersionToDraft(apiClient, projectId, surveyId, versionNumber),
    onSuccess: (version) => {
      const queryKey = surveyVersionKeys.list(projectId, surveyId)
      queryClient.setQueryData<SurveyVersionOut[]>(queryKey, (current) => {
        const next = current ? [...current, version] : [version]
        saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}

export function usePublishSurveyVersion(projectId: number, surveyId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (versionNumber: number) => publishSurveyVersion(apiClient, projectId, surveyId, versionNumber),
    onSuccess: (updated) => {
      const queryKey = surveyVersionKeys.list(projectId, surveyId)
      queryClient.setQueryData<SurveyVersionOut[]>(queryKey, (current) => {
        const next = current?.map((v) => (v.version_number === updated.version_number ? updated : v))
        if (next) saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}

export function useArchiveSurveyVersion(projectId: number, surveyId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (versionNumber: number) => archiveSurveyVersion(apiClient, projectId, surveyId, versionNumber),
    onSuccess: (updated) => {
      const queryKey = surveyVersionKeys.list(projectId, surveyId)
      queryClient.setQueryData<SurveyVersionOut[]>(queryKey, (current) => {
        const next = current?.map((v) => (v.version_number === updated.version_number ? updated : v))
        if (next) saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}
