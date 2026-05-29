// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { ChangeEmailRequest, ChangeUsernameRequest, CurrentUserProfileResponses, CurrentUserResponses, PasswordChangeTicketResponses, ProjectInvitationResponses, ProjectMemberResponses, UpdateProfileRequest } from "./types.gen";

export async function getMyProfile(apiClient: OpenApiFetchClient): Promise<CurrentUserProfileResponses> {
  const { data, error } = await apiClient.GET(`/api/v1/me/profile`);
  if (error) throw error;
  return data;
}

export async function updateMyProfile(apiClient: OpenApiFetchClient, body: UpdateProfileRequest): Promise<CurrentUserResponses> {
  const { data, error } = await apiClient.PATCH(`/api/v1/me/profile`, { body: body as never });
  if (error) throw error;
  return data;
}

export async function changeEmail(apiClient: OpenApiFetchClient, body: ChangeEmailRequest): Promise<void> {
  const { error } = await apiClient.POST(`/api/v1/me/change-email`, { body: body as never });
  if (error) throw error;
}

export async function changeUsername(apiClient: OpenApiFetchClient, body: ChangeUsernameRequest): Promise<void> {
  const { error } = await apiClient.POST(`/api/v1/me/change-username`, { body: body as never });
  if (error) throw error;
}

export async function changePassword(apiClient: OpenApiFetchClient): Promise<PasswordChangeTicketResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/me/change-password`);
  if (error) throw error;
  return data;
}

export async function clearMfa(apiClient: OpenApiFetchClient): Promise<void> {
  const { error } = await apiClient.POST(`/api/v1/me/clear-mfa`);
  if (error) throw error;
}

export async function resendVerification(apiClient: OpenApiFetchClient): Promise<void> {
  const { error } = await apiClient.POST(`/api/v1/me/resend-verification`);
  if (error) throw error;
}

export async function deleteMyAccount(apiClient: OpenApiFetchClient): Promise<void> {
  const { error } = await apiClient.DELETE(`/api/v1/me`);
  if (error) throw error;
}

export async function getMyInvitations(apiClient: OpenApiFetchClient): Promise<ProjectInvitationResponses[]> {
  const { data, error } = await apiClient.GET(`/api/v1/me/invitations`);
  if (error) throw error;
  return data;
}

export async function acceptInvitation(apiClient: OpenApiFetchClient, invitation_id: number): Promise<ProjectMemberResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/me/invitations/{invitation_id}/accept`, { params: { path: { invitation_id } } });
  if (error) throw error;
  return data;
}

export async function declineInvitation(apiClient: OpenApiFetchClient, invitation_id: number): Promise<void> {
  const { error } = await apiClient.POST(`/api/v1/me/invitations/{invitation_id}/decline`, { params: { path: { invitation_id } } });
  if (error) throw error;
}
