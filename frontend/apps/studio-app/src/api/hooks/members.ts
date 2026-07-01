import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { usePolicyQuery } from '@/lib/query/usePolicyQuery'
import { QUERY_POLICIES } from '@/lib/query/queryPolicy'
import type { components } from '@/api/generated/schema'

export type ProjectMemberOut = components['schemas']['ProjectMemberResponses']
export type ProjectInvitationOut = components['schemas']['ProjectInvitationResponses']

const memberKeys = {
  list: (projectId: number) => ['members', 'project', projectId] as const,
  invitations: (projectId: number) => ['invitations', 'project', projectId] as const,
  myInvitations: () => ['me', 'invitations'] as const,
  resolveByToken: (token: string) => ['invitations', 'resolve', token] as const,
}

// ─── Project members ──────────────────────────────────────────────────────────

export function useProjectMembers(projectId: number | null) {
  return usePolicyQuery({
    queryKey: memberKeys.list(projectId ?? 0),
    enabled: projectId != null && projectId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/studio/projects/{project_id}/members', {
        params: { path: { project_id: projectId! } },
      })
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.projectMembers,
  })
}

export function useUpdateProjectMember(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ membershipId, body }: { membershipId: number; body: components['schemas']['UpdateMemberRequest'] }) => {
      const { data, error } = await apiClient.PATCH(
        '/api/v1/studio/projects/{project_id}/members/{membership_id}',
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
        '/api/v1/studio/projects/{project_id}/members/{membership_id}',
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
  return usePolicyQuery({
    queryKey: memberKeys.invitations(projectId ?? 0),
    enabled: projectId != null && projectId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/studio/projects/{project_id}/invitations', {
        params: { path: { project_id: projectId! } },
      })
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.projectInvitations,
  })
}

export function useSendInvitation(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: components['schemas']['SendInvitationRequest']) => {
      const { data, error } = await apiClient.POST('/api/v1/studio/projects/{project_id}/invitations', {
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
        '/api/v1/studio/projects/{project_id}/invitations/{invitation_id}',
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

export function useMyInvitations(enabled = true) {
  return usePolicyQuery({
    queryKey: memberKeys.myInvitations(),
    enabled,
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/account/invitations')
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.myInvitations,
  })
}

export function useAcceptInvitation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (invitationId: number) => {
      const { data, error } = await apiClient.POST(
        '/api/v1/account/invitations/{invitation_id}/accept',
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

// ─── Public invitation resolution (pre-login token flow) ──────────────────────

export function useResolveInvitationByToken(token: string | null) {
  return usePolicyQuery({
    queryKey: memberKeys.resolveByToken(token ?? ''),
    enabled: token != null && token.length > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        '/api/v1/account/invitations/resolve/{token}',
        { params: { path: { token: token! } } },
      )
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.projectInvitations,
  })
}

export function useAcceptInvitationByToken() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (token: string) => {
      const { data, error } = await apiClient.POST(
        '/api/v1/account/invitations/resolve/{token}/accept',
        { params: { path: { token } } },
      )
      if (error) throw error
      return data
    },
    onSuccess: (_data, token) => {
      void queryClient.invalidateQueries({ queryKey: memberKeys.myInvitations() })
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
      void queryClient.invalidateQueries({ queryKey: memberKeys.resolveByToken(token) })
    },
  })
}

export function useDeclineInvitation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (invitationId: number) => {
      const { error } = await apiClient.POST(
        '/api/v1/account/invitations/{invitation_id}/decline',
        { params: { path: { invitation_id: invitationId } } },
      )
      if (error) throw error
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: memberKeys.myInvitations() })
    },
  })
}
