// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { CreateProjectRequest, MyProjectPermissionsResponses, ProjectResponses, UpdateProjectRequest } from "./types.gen";

export async function listProjects(apiClient: OpenApiFetchClient): Promise<ProjectResponses[]> {
  const { data, error } = await apiClient.GET(`/api/v1/projects`);
  if (error) throw error;
  return data;
}

export async function createProject(apiClient: OpenApiFetchClient, body: CreateProjectRequest): Promise<ProjectResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/projects`, { body: body as never });
  if (error) throw error;
  return data;
}

export async function getProject(apiClient: OpenApiFetchClient, project_id: number): Promise<ProjectResponses> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}`, { params: { path: { project_id } } });
  if (error) throw error;
  return data;
}

export async function updateProject(apiClient: OpenApiFetchClient, project_id: number, body: UpdateProjectRequest): Promise<ProjectResponses> {
  const { data, error } = await apiClient.PATCH(`/api/v1/projects/{project_id}`, { params: { path: { project_id } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function deleteProject(apiClient: OpenApiFetchClient, project_id: number): Promise<void> {
  const { error } = await apiClient.DELETE(`/api/v1/projects/{project_id}`, { params: { path: { project_id } } });
  if (error) throw error;
}

export async function getMyProjectPermissions(apiClient: OpenApiFetchClient, project_id: number): Promise<MyProjectPermissionsResponses> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/my-permissions`, { params: { path: { project_id } } });
  if (error) throw error;
  return data;
}
