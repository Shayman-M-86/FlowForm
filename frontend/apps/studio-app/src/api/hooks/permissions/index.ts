import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { permissionKeys } from './queryKeys'
import { STALE } from '@/lib/query/queryClient'
import type { FlowFormPermission } from '@/api/generated/rbac.gen'

export type { FlowFormPermission as ProjectPermission }
export { permissionKeys }

export function useProjectPermissions(projectId: number | null) {
  return useQuery({
    queryKey: permissionKeys.project(projectId ?? 0),
    enabled: projectId != null && projectId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        '/api/v1/projects/{project_id}/my-permissions',
        { params: { path: { project_id: projectId! } } },
      )
      if (error) throw error
      return data.permissions as string[]
    },
    staleTime: STALE.STATIC,
  })
}

export function useHasProjectPermission(projectId: number | null, permission: FlowFormPermission): boolean {
  const { data } = useProjectPermissions(projectId)
  return data?.includes(permission) ?? false
}

export function useSurveyPermissions(projectId: number | null, surveyId: number | null) {
  return useQuery({
    queryKey: permissionKeys.survey(projectId ?? 0, surveyId ?? 0),
    enabled: projectId != null && projectId > 0 && surveyId != null && surveyId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/my-permissions',
        { params: { path: { project_id: projectId!, survey_id: surveyId! } } },
      )
      if (error) throw error
      return data.permissions as string[]
    },
    staleTime: STALE.STATIC,
  })
}

export function useHasSurveyPermission(projectId: number | null, surveyId: number | null, permission: FlowFormPermission): boolean {
  const { data } = useSurveyPermissions(projectId, surveyId)
  return data?.includes(permission) ?? false
}
