// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { CreatePublicLinkRequest, CreatePublicLinkResponses, ListPublicLinksResponses, PublicLinkResponses, UpdatePublicLinkRequest } from "./types.gen";

export async function listPublicLinks(apiClient: OpenApiFetchClient, project_id: number, survey_id: number): Promise<ListPublicLinksResponses> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/surveys/{survey_id}/links`, { params: { path: { project_id, survey_id } } });
  if (error) throw error;
  return data;
}

export async function createPublicLink(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, body: CreatePublicLinkRequest): Promise<CreatePublicLinkResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/projects/{project_id}/surveys/{survey_id}/links`, { params: { path: { project_id, survey_id } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function updatePublicLink(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, link_id: number, body: UpdatePublicLinkRequest): Promise<PublicLinkResponses> {
  const { data, error } = await apiClient.PATCH(`/api/v1/projects/{project_id}/surveys/{survey_id}/links/{link_id}`, { params: { path: { project_id, survey_id, link_id } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function deletePublicLink(apiClient: OpenApiFetchClient, project_id: number, survey_id: number, link_id: number): Promise<void> {
  const { error } = await apiClient.DELETE(`/api/v1/projects/{project_id}/surveys/{survey_id}/links/{link_id}`, { params: { path: { project_id, survey_id, link_id } } });
  if (error) throw error;
}
