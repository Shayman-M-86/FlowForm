import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { STALE, buildQueryOptions } from '@/lib/query/queryClient'
import { useCooldownEnabled } from '@/lib/query/useCooldownQuery'
import type { components } from '@/api/generated/schema'

export type ProjectMemberOut = components['schemas']['ProjectMemberResponses']
export type ProjectInvitationOut = components['schemas']['ProjectInvitationResponses']

const memberKeys = {
  list: (projectId: number) => ['members', 'project', projectId] as const,
  invitations: (projectId: number) => ['invitations', 'project', projectId] as const,
  myInvitations: () => ['me', 'invitations'] as const,
}

// ─── Project members ──────────────────────────────────────────────────────────

export function useProjectMembers(projectId: number | null) {
  return useQuery({
    queryKey: memberKeys.list(projectId ?? 0),
    enabled: projectId != null && projectId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/members', {
        params: { path: { project_id: projectId! } },
      })
      if (error) throw error
      return data
    },
    staleTime: STALE.SLOW,
  })
}

export function useUpdateProjectMember(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ membershipId, body }: { membershipId: number; body: components['schemas']['UpdateMemberRequest'] }) => {
      const { data, error } = await apiClient.PATCH(
        '/api/v1/projects/{project_id}/members/{membership_id}',
        { params: { path: { project_id: projectId, membership_id: membershipId } }, body },
      )
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: memberKeys.list(projectId) })
    },
  })
}

export function useDeleteProjectMember(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (membershipId: number) => {
      const { error } = await apiClient.DELETE(
        '/api/v1/projects/{project_id}/members/{membership_id}',
        { params: { path: { project_id: projectId, membership_id: membershipId } } },
      )
      if (error) throw error
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: memberKeys.list(projectId) })
    },
  })
}

// ─── Project invitations ──────────────────────────────────────────────────────

export function useProjectInvitations(projectId: number | null) {
  return useQuery({
    queryKey: memberKeys.invitations(projectId ?? 0),
    enabled: projectId != null && projectId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/invitations', {
        params: { path: { project_id: projectId! } },
      })
      if (error) throw error
      return data
    },
    staleTime: STALE.ACTIVE,
  })
}

export function useSendInvitation(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: components['schemas']['SendInvitationRequest']) => {
      const { data, error } = await apiClient.POST('/api/v1/projects/{project_id}/invitations', {
        params: { path: { project_id: projectId } },
        body,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: memberKeys.invitations(projectId) })
    },
  })
}

export function useRevokeInvitation(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (invitationId: number) => {
      const { error } = await apiClient.DELETE(
        '/api/v1/projects/{project_id}/invitations/{invitation_id}',
        { params: { path: { project_id: projectId, invitation_id: invitationId } } },
      )
      if (error) throw error
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: memberKeys.invitations(projectId) })
    },
  })
}

// ─── My invitations (sidebar notifications) ───────────────────────────────────

const MY_INVITATIONS_POLICY = {
  staleTime:   'SLOW',
  persist:     true,
  pollMs:      5 * 60 * 1000,
  cooldownMs:  15_000,
  windowFocus: true,
} as const

export function useMyInvitations() {
  const enabled = useCooldownEnabled('me.invitations', MY_INVITATIONS_POLICY.cooldownMs)
  return useQuery({
    queryKey: memberKeys.myInvitations(),
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/me/invitations')
      if (error) throw error
      return data
    },
    enabled,
    ...buildQueryOptions(MY_INVITATIONS_POLICY),
  })
}

export function useAcceptInvitation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (invitationId: number) => {
      const { data, error } = await apiClient.POST(
        '/api/v1/me/invitations/{invitation_id}/accept',
        { params: { path: { invitation_id: invitationId } } },
      )
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: memberKeys.myInvitations() })
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useDeclineInvitation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (invitationId: number) => {
      const { error } = await apiClient.POST(
        '/api/v1/me/invitations/{invitation_id}/decline',
        { params: { path: { invitation_id: invitationId } } },
      )
      if (error) throw error
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: memberKeys.myInvitations() })
    },
  })
}
