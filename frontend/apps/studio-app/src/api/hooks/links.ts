import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { usePolicyQuery } from '@/lib/query/usePolicyQuery'
import { QUERY_POLICIES } from '@/lib/query/queryPolicy'
import type { components } from '@/api/generated/schema'

export type PublicLinkOut = components['schemas']['PublicLinkResponses']

const linkKeys = {
  list: (projectId: number, surveyId: number) =>
    ['links', 'project', projectId, 'survey', surveyId] as const,
}

export function usePublicLinks(projectId: number | null, surveyId: number | null) {
  return usePolicyQuery({
    queryKey: linkKeys.list(projectId ?? 0, surveyId ?? 0),
    enabled: projectId != null && projectId > 0 && surveyId != null && surveyId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/links',
        { params: { path: { project_id: projectId!, survey_id: surveyId! } } },
      )
      if (error) throw error
      return data.links
    },
    policy: QUERY_POLICIES.publicLinks,
  })
}

export function useCreatePublicLink(projectId: number | null, surveyId: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: components['schemas']['CreatePublicLinkRequest']) => {
      if (projectId == null || surveyId == null) throw new Error('projectId and surveyId are required')
      const { data, error } = await apiClient.POST(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/links',
        { params: { path: { project_id: projectId, survey_id: surveyId } }, body },
      )
      if (error) throw error
      return data
    },
    onSuccess: () => {
      if (projectId != null && surveyId != null) {
        void queryClient.invalidateQueries({ queryKey: linkKeys.list(projectId, surveyId) })
      }
    },
  })
}

export function useUpdatePublicLink(projectId: number | null, surveyId: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ linkId, body }: { linkId: number; body: components['schemas']['UpdatePublicLinkRequest'] }) => {
      if (projectId == null || surveyId == null) throw new Error('projectId and surveyId are required')
      const { data, error } = await apiClient.PATCH(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/links/{link_id}',
        { params: { path: { project_id: projectId, survey_id: surveyId, link_id: linkId } }, body },
      )
      if (error) throw error
      return data
    },
    onSuccess: () => {
      if (projectId != null && surveyId != null) {
        void queryClient.invalidateQueries({ queryKey: linkKeys.list(projectId, surveyId) })
      }
    },
  })
}

export function useDeletePublicLink(projectId: number | null, surveyId: number | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (linkId: number) => {
      if (projectId == null || surveyId == null) throw new Error('projectId and surveyId are required')
      const { error } = await apiClient.DELETE(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/links/{link_id}',
        { params: { path: { project_id: projectId, survey_id: surveyId, link_id: linkId } } },
      )
      if (error) throw error
    },
    onSuccess: () => {
      if (projectId != null && surveyId != null) {
        void queryClient.invalidateQueries({ queryKey: linkKeys.list(projectId, surveyId) })
      }
    },
  })
}
