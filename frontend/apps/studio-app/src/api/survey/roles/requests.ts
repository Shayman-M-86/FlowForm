import type { OpenApiFetchClient } from '../../openapi'
import type { CreateSurveyRoleRequest, SurveyRoleOut, UpdateSurveyRoleRequest } from './types'

export async function getSurveyRoles(
  apiClient: OpenApiFetchClient,
  project_id: number,
): Promise<SurveyRoleOut[]> {
  const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/survey-roles', {
    params: { path: { project_id } },
  })
  if (error) throw error
  return data
}

export async function createSurveyRole(
  apiClient: OpenApiFetchClient,
  project_id: number,
  body: CreateSurveyRoleRequest,
): Promise<SurveyRoleOut> {
  const { data, error } = await apiClient.POST('/api/v1/projects/{project_id}/survey-roles', {
    params: { path: { project_id } },
    body,
  })
  if (error) throw error
  return data
}

export async function updateSurveyRole(
  apiClient: OpenApiFetchClient,
  project_id: number,
  role_id: number,
  body: UpdateSurveyRoleRequest,
): Promise<SurveyRoleOut> {
  const { data, error } = await apiClient.PATCH(
    '/api/v1/projects/{project_id}/survey-roles/{role_id}',
    { params: { path: { project_id, role_id } }, body },
  )
  if (error) throw error
  return data
}

export async function deleteSurveyRole(
  apiClient: OpenApiFetchClient,
  project_id: number,
  role_id: number,
): Promise<void> {
  const { error } = await apiClient.DELETE(
    '/api/v1/projects/{project_id}/survey-roles/{role_id}',
    { params: { path: { project_id, role_id } } },
  )
  if (error) throw error
}
