import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOpenApiClient } from '../../openapi'
import { loadCachedQuery, loadCachedQueryUpdatedAt, saveCachedQuery } from '../../queryStorage'
import { projectKeys } from '../projects/hooks'
import { acceptInvitation, declineInvitation, deleteProjectMember, getMyInvitations, getProjectInvitations, getProjectMembers, revokeInvitation, sendInvitation, updateProjectMember } from './requests'
import type { ProjectInvitationOut, ProjectMemberOut, SendInvitationRequest, UpdateMemberRequest } from './types'

const FIFTEEN_SECONDS = 15 * 1000
const TWO_MINUTES = 2 * 60 * 1000

export const memberKeys = {
  all: () => ['members'] as const,
  list: (projectId: number | null) => [...memberKeys.all(), 'list', projectId] as const,
  detail: (projectId: number, membershipId: number) =>
    [...memberKeys.all(), 'detail', projectId, membershipId] as const,
  invitations: (projectId: number | null) => [...memberKeys.all(), 'invitations', projectId] as const,
}

export const myInvitationKeys = {
  all: () => ['my-invitations'] as const,
}

export function useMyInvitations() {
  const apiClient = useOpenApiClient()
  const queryKey = myInvitationKeys.all()

  return useQuery({
    queryKey,
    queryFn: async () => {
      const invitations = await getMyInvitations(apiClient)
      saveCachedQuery(queryKey, invitations)
      return invitations
    },
    staleTime: FIFTEEN_SECONDS,
    initialData: loadCachedQuery<ProjectInvitationOut[]>(queryKey, FIFTEEN_SECONDS),
    initialDataUpdatedAt: () => loadCachedQueryUpdatedAt(queryKey),
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

export function useProjectMembers(projectId: number | null) {
  const apiClient = useOpenApiClient()
  const queryKey = memberKeys.list(projectId)

  return useQuery({
    queryKey,
    queryFn: async () => {
      if (projectId === null) throw new Error('Project id is required')
      const members = await getProjectMembers(apiClient, projectId)
      saveCachedQuery(queryKey, members)
      return members
    },
    enabled: projectId !== null && projectId > 0,
    staleTime: TWO_MINUTES,
    initialData: projectId !== null && projectId > 0
      ? loadCachedQuery<ProjectMemberOut[]>(queryKey, TWO_MINUTES)
      : undefined,
    initialDataUpdatedAt: () => projectId !== null && projectId > 0 ? loadCachedQueryUpdatedAt(queryKey) : undefined,
  })
}

export function useProjectInvitations(projectId: number | null) {
  const apiClient = useOpenApiClient()
  const queryKey = memberKeys.invitations(projectId)

  return useQuery({
    queryKey,
    queryFn: async () => {
      if (projectId === null) throw new Error('Project id is required')
      const invitations = await getProjectInvitations(apiClient, projectId)
      saveCachedQuery(queryKey, invitations)
      return invitations
    },
    enabled: projectId !== null && projectId > 0,
    staleTime: TWO_MINUTES,
    initialData: projectId !== null && projectId > 0
      ? loadCachedQuery<ProjectInvitationOut[]>(queryKey, TWO_MINUTES)
      : undefined,
    initialDataUpdatedAt: () => projectId !== null && projectId > 0 ? loadCachedQueryUpdatedAt(queryKey) : undefined,
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
      const queryKey = memberKeys.list(projectId)
      queryClient.setQueryData<ProjectMemberOut[]>(queryKey, (current) => {
        const next = current?.map((m) => (m.id === updated.id ? updated : m))
        if (next) saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}

export function useDeleteProjectMember(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (membershipId: number) => deleteProjectMember(apiClient, projectId, membershipId),
    onSuccess: (_result, membershipId) => {
      const queryKey = memberKeys.list(projectId)
      queryClient.setQueryData<ProjectMemberOut[]>(queryKey, (current) => {
        const next = current?.filter((m) => m.id !== membershipId)
        if (next) saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}
