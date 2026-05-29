// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { AssignSurveyMemberRoleRequest, SurveyMemberRoleResponses, UpdateSurveyMemberRoleRequest } from "./types.gen";

export async function listSurveyMembers(apiClient: OpenApiFetchClient, project_id: number, survey_id: number): Promise<SurveyMemberRoleResponses[]> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/surveys/{survey_id}/members`, { params: { path: { project_id, survey_id } } });
  if (error) throw error;
  return data;
}

export async function assignSurveyMemberRole(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, body: AssignSurveyMemberRoleRequest): Promise<SurveyMemberRoleResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/projects/{project_id}/surveys/{survey_id}/members`, { params: { path: { project_id, survey_id } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function updateSurveyMemberRole(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, membership_id: number, body: UpdateSurveyMemberRoleRequest): Promise<SurveyMemberRoleResponses> {
  const { data, error } = await apiClient.PATCH(`/api/v1/projects/{project_id}/surveys/{survey_id}/members/{membership_id}`, { params: { path: { project_id, survey_id, membership_id } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function removeSurveyMemberRole(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, membership_id: number): Promise<void> {
  const { error } = await apiClient.DELETE(`/api/v1/projects/{project_id}/surveys/{survey_id}/members/{membership_id}`, { params: { path: { project_id, survey_id, membership_id } } });
  if (error) throw error;
}
