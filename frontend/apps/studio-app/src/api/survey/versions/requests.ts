import type { OpenApiFetchClient } from '../../openapi'
import type { SurveyVersionOut } from './types'

export async function getSurveyVersions(
  apiClient: OpenApiFetchClient,
  project_id: number,
  survey_id: number,
): Promise<SurveyVersionOut[]> {
  const { data, error } = await apiClient.GET(
    '/api/v1/projects/{project_id}/surveys/{survey_id}/versions',
    { params: { path: { project_id, survey_id } } },
  )
  if (error) throw error
  return data
}

export async function createSurveyVersion(
  apiClient: OpenApiFetchClient,
  project_id: number,
  survey_id: number,
): Promise<SurveyVersionOut> {
  const { data, error } = await apiClient.POST(
    '/api/v1/projects/{project_id}/surveys/{survey_id}/versions',
    { params: { path: { project_id, survey_id } } },
  )
  if (error) throw error
  return data
}

export async function copyVersionToDraft(
  apiClient: OpenApiFetchClient,
  project_id: number,
  survey_id: number,
  version_number: number,
): Promise<SurveyVersionOut> {
  const { data, error } = await apiClient.POST(
    '/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/copy-to-draft',
    { params: { path: { project_id, survey_id, version_number } } },
  )
  if (error) throw error
  return data
}

export async function publishSurveyVersion(
  apiClient: OpenApiFetchClient,
  project_id: number,
  survey_id: number,
  version_number: number,
): Promise<SurveyVersionOut> {
  const { data, error } = await apiClient.POST(
    '/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/publish',
    { params: { path: { project_id, survey_id, version_number } } },
  )
  if (error) throw error
  return data
}

export async function archiveSurveyVersion(
  apiClient: OpenApiFetchClient,
  project_id: number,
  survey_id: number,
  version_number: number,
): Promise<SurveyVersionOut> {
  const { data, error } = await apiClient.POST(
    '/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/archive',
    { params: { path: { project_id, survey_id, version_number } } },
  )
  if (error) throw error
  return data
}
