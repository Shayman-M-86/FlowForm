import type { OpenApiFetchClient } from '../../openapi'
import type { CreatePublicLinkRequest, PublicLinkOut, UpdatePublicLinkInput } from './types'

export async function getPublicLinks(
  apiClient: OpenApiFetchClient,
  project_id: number,
  survey_id: number,
): Promise<PublicLinkOut[]> {
  const { data, error } = await apiClient.GET(
    '/api/v1/projects/{project_id}/surveys/{survey_id}/links',
    { params: { path: { project_id, survey_id } } },
  )
  if (error) throw error
  return data.links
}

export async function createPublicLink(
  apiClient: OpenApiFetchClient,
  project_id: number,
  survey_id: number,
  body: CreatePublicLinkRequest,
): Promise<PublicLinkOut> {
  const { data, error } = await apiClient.POST(
    '/api/v1/projects/{project_id}/surveys/{survey_id}/links',
    { params: { path: { project_id, survey_id } }, body },
  )
  if (error) throw error
  return data.link
}

export async function updatePublicLink(
  apiClient: OpenApiFetchClient,
  project_id: number,
  survey_id: number,
  link_id: number,
  body: UpdatePublicLinkInput,
): Promise<PublicLinkOut> {
  const { data, error } = await apiClient.PATCH(
    '/api/v1/projects/{project_id}/surveys/{survey_id}/links/{link_id}',
    { params: { path: { project_id, survey_id, link_id } }, body },
  )
  if (error) throw error
  return data
}

export async function deletePublicLink(
  apiClient: OpenApiFetchClient,
  project_id: number,
  survey_id: number,
  link_id: number,
): Promise<void> {
  const { error } = await apiClient.DELETE(
    '/api/v1/projects/{project_id}/surveys/{survey_id}/links/{link_id}',
    { params: { path: { project_id, survey_id, link_id } } },
  )
  if (error) throw error
}
