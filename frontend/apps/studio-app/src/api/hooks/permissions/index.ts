import { usePolicyQuery } from '@/lib/query/usePolicyQuery'
import { QUERY_POLICIES } from '@/lib/query/queryPolicy'
import { apiClient } from '@/api/client'
import { permissionKeys } from './queryKeys'
import type { FlowFormPermission } from '@/api/generated/rbac.gen'

export type { FlowFormPermission as ProjectPermission }
export { permissionKeys }

export const PERMISSION_REQUIRED_TOOLTIP = {
  surveys: 'You need survey:view permission to access surveys.',
  members: 'You need project:manage_members permission to manage members.',
  roles: 'You need project:manage_roles permission to manage roles.',
  settings: 'You need project:edit or project:delete permission to access settings.',
  surveyBuilder: 'You need survey:edit permission to use the builder.',
  surveyResponses: 'You need submission:view permission to view responses.',
  surveySettings: 'You need survey:edit, archive, delete, or publish permission to access settings.',
} as const

export function useProjectPermissions(projectId: number | null) {
  return usePolicyQuery({
    queryKey: permissionKeys.project(projectId ?? 0),
    enabled: projectId != null && projectId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        '/api/v1/studio/projects/{project_id}/my-permissions',
        { params: { path: { project_id: projectId! } } },
      )
      if (error) throw error
      return data.permissions as string[]
    },
    policy: QUERY_POLICIES.projectPermissions,
  })
}

export function useHasProjectPermission(projectId: number | null, permission: FlowFormPermission): boolean {
  const { data } = useProjectPermissions(projectId)
  return data?.includes(permission) ?? false
}

export function useSurveyPermissions(projectId: number | null, surveyId: number | null) {
  return usePolicyQuery({
    queryKey: permissionKeys.survey(projectId ?? 0, surveyId ?? 0),
    enabled: projectId != null && projectId > 0 && surveyId != null && surveyId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        '/api/v1/studio/projects/{project_id}/surveys/{survey_id}/my-permissions',
        { params: { path: { project_id: projectId!, survey_id: surveyId! } } },
      )
      if (error) throw error
      return data.permissions as string[]
    },
    policy: QUERY_POLICIES.surveyPermissions,
  })
}

export function useHasSurveyPermission(projectId: number | null, surveyId: number | null, permission: FlowFormPermission): boolean {
  const { data } = useSurveyPermissions(projectId, surveyId)
  return data?.includes(permission) ?? false
}
