import type { OpenApiFetchClient } from '../../openapi'
import type { ProjectInvitationOut, ProjectMemberOut, SendInvitationRequest, UpdateMemberRequest } from './types'

export async function getMyInvitations(
  apiClient: OpenApiFetchClient,
): Promise<ProjectInvitationOut[]> {
  const { data, error } = await apiClient.GET('/api/v1/me/invitations')
  if (error) throw error
  return data
}

export async function acceptInvitation(
  apiClient: OpenApiFetchClient,
  invitation_id: number,
): Promise<void> {
  const { error } = await apiClient.POST('/api/v1/me/invitations/{invitation_id}/accept', {
    params: { path: { invitation_id } },
  })
  if (error) throw error
}

export async function declineInvitation(
  apiClient: OpenApiFetchClient,
  invitation_id: number,
): Promise<void> {
  const { error } = await apiClient.POST('/api/v1/me/invitations/{invitation_id}/decline', {
    params: { path: { invitation_id } },
  })
  if (error) throw error
}

export async function sendInvitation(
  apiClient: OpenApiFetchClient,
  project_id: number,
  body: SendInvitationRequest,
): Promise<ProjectInvitationOut> {
  const { data, error } = await apiClient.POST('/api/v1/projects/{project_id}/invitations', {
    params: { path: { project_id } },
    body,
  })
  if (error) throw error
  return data
}

export async function getProjectInvitations(
  apiClient: OpenApiFetchClient,
  project_id: number,
): Promise<ProjectInvitationOut[]> {
  const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/invitations', {
    params: { path: { project_id } },
  })
  if (error) throw error
  return data
}

export async function revokeInvitation(
  apiClient: OpenApiFetchClient,
  project_id: number,
  invitation_id: number,
): Promise<void> {
  const { error } = await apiClient.DELETE(
    '/api/v1/projects/{project_id}/invitations/{invitation_id}',
    { params: { path: { project_id, invitation_id } } },
  )
  if (error) throw error
}

export async function getProjectMembers(
  apiClient: OpenApiFetchClient,
  project_id: number,
): Promise<ProjectMemberOut[]> {
  const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/members', {
    params: { path: { project_id } },
  })
  if (error) throw error
  return data
}

export async function updateProjectMember(
  apiClient: OpenApiFetchClient,
  project_id: number,
  membership_id: number,
  body: UpdateMemberRequest,
): Promise<ProjectMemberOut> {
  const { data, error } = await apiClient.PATCH(
    '/api/v1/projects/{project_id}/members/{membership_id}',
    { params: { path: { project_id, membership_id } }, body },
  )
  if (error) throw error
  return data
}

export async function deleteProjectMember(
  apiClient: OpenApiFetchClient,
  project_id: number,
  membership_id: number,
): Promise<void> {
  const { error } = await apiClient.DELETE(
    '/api/v1/projects/{project_id}/members/{membership_id}',
    { params: { path: { project_id, membership_id } } },
  )
  if (error) throw error
}
