import type { OpenApiFetchClient } from '../../openapi'
import type { NodeOut, CreateNodeRequest, UpdateNodeRequest } from './types'

export async function listNodes(
  apiClient: OpenApiFetchClient,
  project_id: number,
  survey_id: number,
  version_number: number,
): Promise<NodeOut[]> {
  const { data, error } = await apiClient.GET(
    '/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/nodes',
    { params: { path: { project_id, survey_id, version_number } } },
  )
  if (error) throw error
  return data
}

export async function createNode(
  apiClient: OpenApiFetchClient,
  project_id: number,
  survey_id: number,
  version_number: number,
  body: CreateNodeRequest,
): Promise<NodeOut> {
  const { data, error } = await apiClient.POST(
    '/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/nodes',
    { params: { path: { project_id, survey_id, version_number } }, body },
  )
  if (error) throw error
  return data
}

export async function updateNode(
  apiClient: OpenApiFetchClient,
  project_id: number,
  survey_id: number,
  version_number: number,
  node_id: number,
  body: UpdateNodeRequest,
): Promise<NodeOut> {
  const { data, error } = await apiClient.PATCH(
    '/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/nodes/{node_id}',
    { params: { path: { project_id, survey_id, version_number, node_id } }, body },
  )
  if (error) throw error
  return data
}

export async function deleteNode(
  apiClient: OpenApiFetchClient,
  project_id: number,
  survey_id: number,
  version_number: number,
  node_id: number,
): Promise<void> {
  const { error } = await apiClient.DELETE(
    '/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/nodes/{node_id}',
    { params: { path: { project_id, survey_id, version_number, node_id } } },
  )
  if (error) throw error
}
