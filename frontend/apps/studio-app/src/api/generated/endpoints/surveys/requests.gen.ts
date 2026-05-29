// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { CreateSurveyRequest, SurveyResponses, UpdateSurveyRequest } from "./types.gen";

export async function listSurveys(apiClient: OpenApiFetchClient, project_id: number): Promise<SurveyResponses[]> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/surveys`, { params: { path: { project_id } } });
  if (error) throw error;
  return data;
}

export async function createSurvey(apiClient: OpenApiFetchClient, project_id: number, body: CreateSurveyRequest): Promise<SurveyResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/projects/{project_id}/surveys`, { params: { path: { project_id } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function getSurvey(apiClient: OpenApiFetchClient, project_id: number, survey_id: number): Promise<SurveyResponses> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/surveys/{survey_id}`, { params: { path: { project_id, survey_id } } });
  if (error) throw error;
  return data;
}

export async function updateSurvey(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, body: UpdateSurveyRequest): Promise<SurveyResponses> {
  const { data, error } = await apiClient.PATCH(`/api/v1/projects/{project_id}/surveys/{survey_id}`, { params: { path: { project_id, survey_id } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function deleteSurvey(apiClient: OpenApiFetchClient, project_id: number, survey_id: number): Promise<void> {
  const { error } = await apiClient.DELETE(`/api/v1/projects/{project_id}/surveys/{survey_id}`, { params: { path: { project_id, survey_id } } });
  if (error) throw error;
}
