// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { SurveyVersionResponses } from "./types.gen";

export async function listVersions(apiClient: OpenApiFetchClient, project_id: number, survey_id: number): Promise<SurveyVersionResponses[]> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions`, { params: { path: { project_id, survey_id } } });
  if (error) throw error;
  return data;
}

export async function createVersion(apiClient: OpenApiFetchClient, project_id: number, survey_id: number): Promise<SurveyVersionResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions`, { params: { path: { project_id, survey_id } } });
  if (error) throw error;
  return data;
}

export async function copyVersionToDraft(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, version_number: number): Promise<SurveyVersionResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/copy-to-draft`, { params: { path: { project_id, survey_id, version_number } } });
  if (error) throw error;
  return data;
}

export async function getVersion(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, version_number: number): Promise<SurveyVersionResponses> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}`, { params: { path: { project_id, survey_id, version_number } } });
  if (error) throw error;
  return data;
}

export async function publishVersion(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, version_number: number): Promise<SurveyVersionResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/publish`, { params: { path: { project_id, survey_id, version_number } } });
  if (error) throw error;
  return data;
}

export async function archiveVersion(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, version_number: number): Promise<SurveyVersionResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/archive`, { params: { path: { project_id, survey_id, version_number } } });
  if (error) throw error;
  return data;
}
