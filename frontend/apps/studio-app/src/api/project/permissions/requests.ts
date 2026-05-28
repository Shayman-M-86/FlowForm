import type { OpenApiFetchClient } from '../../openapi'
import type { ProjectPermission } from './types'

export async function getMyProjectPermissions(
  apiClient: OpenApiFetchClient,
  projectId: number,
): Promise<ProjectPermission[]> {
  const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/my-permissions', {
    params: { path: { project_id: projectId } },
  })
  if (error) throw error
  return data.permissions
}
