// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { CreateProjectRoleRequest, ProjectRoleResponses, UpdateProjectRoleRequest } from "./types.gen";

export async function listRoles(apiClient: OpenApiFetchClient, project_id: number): Promise<ProjectRoleResponses[]> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/roles`, { params: { path: { project_id } } });
  if (error) throw error;
  return data;
}

export async function createRole(apiClient: OpenApiFetchClient, project_id: number, body: CreateProjectRoleRequest): Promise<ProjectRoleResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/projects/{project_id}/roles`, { params: { path: { project_id } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function updateRole(apiClient: OpenApiFetchClient, project_id: number, role_id: number, body: UpdateProjectRoleRequest): Promise<ProjectRoleResponses> {
  const { data, error } = await apiClient.PATCH(`/api/v1/projects/{project_id}/roles/{role_id}`, { params: { path: { project_id, role_id } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function deleteRole(apiClient: OpenApiFetchClient, project_id: number, role_id: number): Promise<void> {
  const { error } = await apiClient.DELETE(`/api/v1/projects/{project_id}/roles/{role_id}`, { params: { path: { project_id, role_id } } });
  if (error) throw error;
}
