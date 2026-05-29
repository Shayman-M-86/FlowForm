// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { CreateScoringRuleRequest, ScoringRuleResponses, UpdateScoringRuleRequest } from "./types.gen";

export async function listScoringRules(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, version_number: number): Promise<ScoringRuleResponses[]> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/scoring-rules`, { params: { path: { project_id, survey_id, version_number } } });
  if (error) throw error;
  return data;
}

export async function createScoringRule(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, version_number: number, body: CreateScoringRuleRequest): Promise<ScoringRuleResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/scoring-rules`, { params: { path: { project_id, survey_id, version_number } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function updateScoringRule(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, version_number: number, scoring_rule_id: number, body: UpdateScoringRuleRequest): Promise<ScoringRuleResponses> {
  const { data, error } = await apiClient.PATCH(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/scoring-rules/{scoring_rule_id}`, { params: { path: { project_id, survey_id, version_number, scoring_rule_id } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function deleteScoringRule(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, version_number: number, scoring_rule_id: number): Promise<void> {
  const { error } = await apiClient.DELETE(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/scoring-rules/{scoring_rule_id}`, { params: { path: { project_id, survey_id, version_number, scoring_rule_id } } });
  if (error) throw error;
}
