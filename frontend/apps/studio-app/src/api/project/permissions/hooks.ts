import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useOpenApiClient } from '../../openapi'
import { getMyProjectPermissions } from '../../generated/endpoints/projects/requests.gen'
import { getMySurveyPermissions } from '../../generated/endpoints/surveys/requests.gen'
import { loadCachedQuery, loadCachedQueryUpdatedAt, saveCachedQuery, clearQueryCache } from '../../queryStorage'
import type { ProjectPermission, SurveyPermission } from './types'

const FIVE_MINUTES = 5 * 60 * 1000

export const permissionKeys = {
  all: () => ['permissions'] as const,
  project: (projectId: number) => [...permissionKeys.all(), 'project', projectId] as const,
  survey: (projectId: number, surveyId: number) => [...permissionKeys.all(), 'survey', projectId, surveyId] as const,
}

export function clearAllCachedPermissions() {
  clearQueryCache()
}

// ─── Project permissions ──────────────────────────────────────────────────────

export function useMyProjectPermissions(projectId: number | null) {
  const apiClient = useOpenApiClient()
  const key = permissionKeys.project(projectId ?? 0)

  return useQuery({
    queryKey: key,
    queryFn: async () => {
      if (projectId === null) throw new Error('projectId required')
      const { permissions } = await getMyProjectPermissions(apiClient, projectId)
      saveCachedQuery(key, permissions)
      return permissions as ProjectPermission[]
    },
    enabled: projectId !== null,
    staleTime: FIVE_MINUTES,
    initialData: projectId !== null ? loadCachedQuery<ProjectPermission[]>(key, FIVE_MINUTES) : undefined,
    initialDataUpdatedAt: () => projectId !== null ? loadCachedQueryUpdatedAt(key) : undefined,
  })
}

export function useHasProjectPermission(projectId: number | null, permission: ProjectPermission): boolean {
  const { data } = useMyProjectPermissions(projectId)
  return data?.includes(permission) ?? false
}

// ─── Survey permissions ───────────────────────────────────────────────────────

export function useMySurveyPermissions(projectId: number | null, surveyId: number | null) {
  const apiClient = useOpenApiClient()
  const key = permissionKeys.survey(projectId ?? 0, surveyId ?? 0)

  return useQuery({
    queryKey: key,
    queryFn: async () => {
      if (projectId === null || surveyId === null) throw new Error('projectId and surveyId required')
      const { permissions } = await getMySurveyPermissions(apiClient, projectId, surveyId)
      saveCachedQuery(key, permissions)
      return permissions as SurveyPermission[]
    },
    enabled: projectId !== null && surveyId !== null,
    staleTime: FIVE_MINUTES,
    initialData: projectId !== null && surveyId !== null ? loadCachedQuery<SurveyPermission[]>(key, FIVE_MINUTES) : undefined,
    initialDataUpdatedAt: () => projectId !== null && surveyId !== null ? loadCachedQueryUpdatedAt(key) : undefined,
  })
}

export function useHasSurveyPermission(projectId: number | null, surveyId: number | null, permission: SurveyPermission): boolean {
  const { data } = useMySurveyPermissions(projectId, surveyId)
  return data?.includes(permission) ?? false
}

// ─── Invalidation ─────────────────────────────────────────────────────────────

export function useInvalidateProjectPermissions() {
  const queryClient = useQueryClient()
  return (projectId: number) => {
    void queryClient.invalidateQueries({ queryKey: permissionKeys.project(projectId) })
  }
}

export function useInvalidateSurveyPermissions() {
  const queryClient = useQueryClient()
  return (projectId: number, surveyId: number) => {
    void queryClient.invalidateQueries({ queryKey: permissionKeys.survey(projectId, surveyId) })
  }
}
