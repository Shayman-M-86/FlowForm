import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { usePolicyQuery } from '@/lib/query/usePolicyQuery'
import { QUERY_POLICIES } from '@/lib/query/queryPolicy'
import type { components } from '@/api/generated/schema'

export type SubjectOut = components['schemas']['SubjectResponse']
export type ParticipantOut = components['schemas']['ParticipantResponses']

const subjectKeys = {
  list: (projectId: number) => ['subjects', 'project', projectId] as const,
  detail: (projectId: number, subjectId: string) => ['subjects', 'project', projectId, subjectId] as const,
}

const participantKeys = {
  list: (projectId: number) => ['participants', 'project', projectId] as const,
}

// ─── Subjects ─────────────────────────────────────────────────────────────────

export function useSubjects(
  projectId: number | null,
  params?: { canonical_status?: 'canonical' | 'alias' | 'all'; is_participant?: boolean | null; search?: string | null; page?: number; page_size?: number },
) {
  return usePolicyQuery({
    queryKey: [...subjectKeys.list(projectId ?? 0), params] as const,
    enabled: projectId != null && projectId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/studio/projects/{project_id}/subjects', {
        params: { path: { project_id: projectId! }, query: params },
      })
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.subjects,
  })
}

export function useSubject(projectId: number | null, subjectId: string | null) {
  return usePolicyQuery({
    queryKey: subjectKeys.detail(projectId ?? 0, subjectId ?? ''),
    enabled: projectId != null && projectId > 0 && subjectId != null,
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/studio/projects/{project_id}/subjects/{subject_id}', {
        params: { path: { project_id: projectId!, subject_id: subjectId! } },
      })
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.subjects,
  })
}

export function useUpdateSubject(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ subjectId, body }: { subjectId: string; body: { subject_code: string } }) => {
      const { data, error } = await apiClient.PATCH('/api/v1/studio/projects/{project_id}/subjects/{subject_id}', {
        params: { path: { project_id: projectId, subject_id: subjectId } },
        body,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: subjectKeys.list(projectId) })
    },
  })
}

// ─── Participants ─────────────────────────────────────────────────────────────

export function useParticipants(
  projectId: number | null,
  params?: { search?: string | null; page?: number; page_size?: number },
) {
  return usePolicyQuery({
    queryKey: [...participantKeys.list(projectId ?? 0), params] as const,
    enabled: projectId != null && projectId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/studio/projects/{project_id}/participants', {
        params: { path: { project_id: projectId! }, query: params },
      })
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.participants,
  })
}

export function useCreateParticipant(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: components['schemas']['CreateParticipantRequest']) => {
      const { data, error } = await apiClient.POST('/api/v1/studio/projects/{project_id}/participants', {
        params: { path: { project_id: projectId } },
        body,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: participantKeys.list(projectId) })
      void queryClient.invalidateQueries({ queryKey: subjectKeys.list(projectId) })
    },
  })
}

export function useUpdateParticipant(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ participantId, body }: { participantId: string; body: components['schemas']['UpdateParticipantRequest'] }) => {
      const { data, error } = await apiClient.PATCH('/api/v1/studio/projects/{project_id}/participants/{participant_id}', {
        params: { path: { project_id: projectId, participant_id: participantId } },
        body,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: participantKeys.list(projectId) })
      void queryClient.invalidateQueries({ queryKey: subjectKeys.list(projectId) })
    },
  })
}

export function useDeleteParticipant(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (participantId: string) => {
      const { error } = await apiClient.DELETE('/api/v1/studio/projects/{project_id}/participants/{participant_id}', {
        params: { path: { project_id: projectId, participant_id: participantId } },
      })
      if (error) throw error
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: participantKeys.list(projectId) })
      void queryClient.invalidateQueries({ queryKey: subjectKeys.list(projectId) })
    },
  })
}
