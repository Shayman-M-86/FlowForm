// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { ProjectInvitationResponses, ProjectMemberResponses, SendInvitationRequest, UpdateMemberRequest } from "./types.gen";

export async function listMembers(apiClient: OpenApiFetchClient, project_id: number): Promise<ProjectMemberResponses[]> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/members`, { params: { path: { project_id } } });
  if (error) throw error;
  return data;
}

export async function listInvitations(apiClient: OpenApiFetchClient, project_id: number): Promise<ProjectInvitationResponses[]> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/invitations`, { params: { path: { project_id } } });
  if (error) throw error;
  return data;
}

export async function sendInvitation(apiClient: OpenApiFetchClient, project_id: number, body: SendInvitationRequest): Promise<ProjectInvitationResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/projects/{project_id}/invitations`, { params: { path: { project_id } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function revokeInvitation(apiClient: OpenApiFetchClient, project_id: number, invitation_id: number): Promise<void> {
  const { error } = await apiClient.DELETE(`/api/v1/projects/{project_id}/invitations/{invitation_id}`, { params: { path: { project_id, invitation_id } } });
  if (error) throw error;
}

export async function updateMember(apiClient: OpenApiFetchClient, project_id: number, membership_id: number, body: UpdateMemberRequest): Promise<ProjectMemberResponses> {
  const { data, error } = await apiClient.PATCH(`/api/v1/projects/{project_id}/members/{membership_id}`, { params: { path: { project_id, membership_id } }, body: body as never });
  if (error) throw error;
  return data;
}

export async function removeMember(apiClient: OpenApiFetchClient, project_id: number, membership_id: number): Promise<void> {
  const { error } = await apiClient.DELETE(`/api/v1/projects/{project_id}/members/{membership_id}`, { params: { path: { project_id, membership_id } } });
  if (error) throw error;
}
