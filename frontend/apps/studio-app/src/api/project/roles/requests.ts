import type { OpenApiFetchClient } from '../../openapi'
import type { CreateProjectRoleRequest, ProjectRoleOut, UpdateProjectRoleRequest } from './types'

export async function getProjectRoles(
  apiClient: OpenApiFetchClient,
  project_id: number,
): Promise<ProjectRoleOut[]> {
  const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/roles', {
    params: { path: { project_id } },
  })
  if (error) throw error
  return data
}

export async function createProjectRole(
  apiClient: OpenApiFetchClient,
  project_id: number,
  body: CreateProjectRoleRequest,
): Promise<ProjectRoleOut> {
  const { data, error } = await apiClient.POST('/api/v1/projects/{project_id}/roles', {
    params: { path: { project_id } },
    body,
  })
  if (error) throw error
  return data
}

export async function updateProjectRole(
  apiClient: OpenApiFetchClient,
  project_id: number,
  role_id: number,
  body: UpdateProjectRoleRequest,
): Promise<ProjectRoleOut> {
  const { data, error } = await apiClient.PATCH(
    '/api/v1/projects/{project_id}/roles/{role_id}',
    { params: { path: { project_id, role_id } }, body },
  )
  if (error) throw error
  return data
}

export async function deleteProjectRole(
  apiClient: OpenApiFetchClient,
  project_id: number,
  role_id: number,
): Promise<void> {
  const { error } = await apiClient.DELETE(
    '/api/v1/projects/{project_id}/roles/{role_id}',
    { params: { path: { project_id, role_id } } },
  )
  if (error) throw error
}
