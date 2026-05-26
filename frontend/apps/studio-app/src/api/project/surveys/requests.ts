import { getProjects, toProjectId } from '../projects/requests'
import type { OpenApiFetchClient } from '../../openapi'
import type { CreateSurveyRequest, SurveyOut, UpdateSurveyRequest } from './types'

async function toProjectAndSurveyId(
  apiClient: OpenApiFetchClient,
  projectRef: string | number,
  surveyRef: string | number,
): Promise<{ project_id: number; survey_id: number }> {
  const project_id =
    typeof projectRef === 'number'
      ? projectRef
      : toProjectId(projectRef, await getProjects(apiClient))

  const numericSurveyRef = typeof surveyRef === 'string' ? parseInt(surveyRef, 10) : surveyRef
  const survey_id = Number.isFinite(numericSurveyRef)
    ? numericSurveyRef
    : await resolveSurveyId(apiClient, project_id, surveyRef as string)

  return { project_id, survey_id }
}

async function resolveSurveyId(
  apiClient: OpenApiFetchClient,
  project_id: number,
  slug: string,
): Promise<number> {
  const surveys = await getSurveys(apiClient, project_id)
  const match = surveys.find((s) => s.public_slug === slug)
  if (!match) throw new Error(`Survey not found: ${slug}`)
  return match.id
}

export async function getSurveys(
  apiClient: OpenApiFetchClient,
  project_id: number,
): Promise<SurveyOut[]> {
  const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/surveys', {
    params: { path: { project_id } },
  })
  if (error) throw error
  return data
}

export async function getSurvey(
  apiClient: OpenApiFetchClient,
  projectRef: string | number,
  surveyRef: string | number,
): Promise<SurveyOut> {
  const { project_id, survey_id } = await toProjectAndSurveyId(apiClient, projectRef, surveyRef)
  const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/surveys/{survey_id}', {
    params: { path: { project_id, survey_id } },
  })
  if (error) throw error
  return data
}

export async function createSurvey(
  apiClient: OpenApiFetchClient,
  project_id: number,
  body: CreateSurveyRequest,
): Promise<SurveyOut> {
  const { data, error } = await apiClient.POST('/api/v1/projects/{project_id}/surveys', {
    params: { path: { project_id } },
    body,
  })
  if (error) throw error
  return data
}

export async function updateSurvey(
  apiClient: OpenApiFetchClient,
  projectRef: string | number,
  surveyRef: string | number,
  body: UpdateSurveyRequest,
): Promise<SurveyOut> {
  const { project_id, survey_id } = await toProjectAndSurveyId(apiClient, projectRef, surveyRef)
  const { data, error } = await apiClient.PATCH(
    '/api/v1/projects/{project_id}/surveys/{survey_id}',
    { params: { path: { project_id, survey_id } }, body },
  )
  if (error) throw error
  return data
}

export async function deleteSurvey(
  apiClient: OpenApiFetchClient,
  projectRef: string | number,
  surveyRef: string | number,
): Promise<void> {
  const { project_id, survey_id } = await toProjectAndSurveyId(apiClient, projectRef, surveyRef)
  const { error } = await apiClient.DELETE('/api/v1/projects/{project_id}/surveys/{survey_id}', {
    params: { path: { project_id, survey_id } },
  })
  if (error) throw error
}
