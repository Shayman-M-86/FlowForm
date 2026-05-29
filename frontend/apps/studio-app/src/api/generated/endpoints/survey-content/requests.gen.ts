// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { CreateNodeRequest, NodeResponses, UpdateNodeRequest } from "./types.gen";

export async function listNodes(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, version_number: number): Promise<NodeResponses[]> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/nodes`, { params: { path: { project_id, survey_id, version_number } } });
  if (error) throw error;
  return data;
}

export async function createNode(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, version_number: number, body: CreateNodeRequest): Promise<NodeResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/nodes`, { params: { path: { project_id, survey_id, version_number } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function getNode(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, version_number: number, node_id: number): Promise<NodeResponses> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/nodes/{node_id}`, { params: { path: { project_id, survey_id, version_number, node_id } } });
  if (error) throw error;
  return data;
}

export async function updateNode(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, version_number: number, node_id: number, body: UpdateNodeRequest): Promise<NodeResponses> {
  const { data, error } = await apiClient.PATCH(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/nodes/{node_id}`, { params: { path: { project_id, survey_id, version_number, node_id } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function deleteNode(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, version_number: number, node_id: number): Promise<void> {
  const { error } = await apiClient.DELETE(`/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/nodes/{node_id}`, { params: { path: { project_id, survey_id, version_number, node_id } } });
  if (error) throw error;
}
