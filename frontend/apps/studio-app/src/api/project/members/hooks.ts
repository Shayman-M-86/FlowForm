import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOpenApiClient } from '../../openapi'
import { projectKeys } from '../projects/hooks'
import { acceptInvitation, declineInvitation, deleteProjectMember, getMyInvitations, getProjectInvitations, getProjectMembers, revokeInvitation, sendInvitation, updateProjectMember } from './requests'
import type { ProjectInvitationOut, ProjectMemberOut, SendInvitationRequest, UpdateMemberRequest } from './types'

export const memberKeys = {
  all: () => ['members'] as const,
  list: (projectId: number) => [...memberKeys.all(), 'list', projectId] as const,
  detail: (projectId: number, membershipId: number) =>
    [...memberKeys.all(), 'detail', projectId, membershipId] as const,
  invitations: (projectId: number) => [...memberKeys.all(), 'invitations', projectId] as const,
}

export const myInvitationKeys = {
  all: () => ['my-invitations'] as const,
}

export function useMyInvitations() {
  const apiClient = useOpenApiClient()

  return useQuery({
    queryKey: myInvitationKeys.all(),
    queryFn: () => getMyInvitations(apiClient),
  })
}

export function useAcceptInvitation() {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (invitationId: number) => acceptInvitation(apiClient, invitationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: myInvitationKeys.all() })
      void queryClient.invalidateQueries({ queryKey: projectKeys.list() })
    },
  })
}

export function useDeclineInvitation() {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (invitationId: number) => declineInvitation(apiClient, invitationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: myInvitationKeys.all() })
    },
  })
}

export function useProjectMembers(projectId: number) {
  const apiClient = useOpenApiClient()

  return useQuery({
    queryKey: memberKeys.list(projectId),
    queryFn: () => getProjectMembers(apiClient, projectId),
  })
}

export function useProjectInvitations(projectId: number) {
  const apiClient = useOpenApiClient()

  return useQuery({
    queryKey: memberKeys.invitations(projectId),
    queryFn: () => getProjectInvitations(apiClient, projectId),
  })
}

export function useRevokeInvitation(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (invitationId: number) => revokeInvitation(apiClient, projectId, invitationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: memberKeys.invitations(projectId) })
    },
  })
}

export function useSendInvitation(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: SendInvitationRequest) => sendInvitation(apiClient, projectId, body),
    onSuccess: (invitation) => {
      queryClient.setQueryData<ProjectInvitationOut[]>(memberKeys.invitations(projectId), (current) =>
        current ? [...current, invitation] : [invitation],
      )
    },
  })
}

export function useUpdateProjectMember(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ membershipId, body }: { membershipId: number; body: UpdateMemberRequest }) =>
      updateProjectMember(apiClient, projectId, membershipId, body),
    onSuccess: (updated) => {
      queryClient.setQueryData<ProjectMemberOut[]>(memberKeys.list(projectId), (current) =>
        current?.map((m) => (m.id === updated.id ? updated : m)),
      )
    },
  })
}

export function useDeleteProjectMember(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (membershipId: number) => deleteProjectMember(apiClient, projectId, membershipId),
    onSuccess: (_result, membershipId) => {
      queryClient.setQueryData<ProjectMemberOut[]>(memberKeys.list(projectId), (current) =>
        current?.filter((m) => m.id !== membershipId),
      )
    },
  })
}
