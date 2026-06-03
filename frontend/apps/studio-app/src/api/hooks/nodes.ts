import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { STALE } from '@/lib/query/queryClient'
import type { components } from '@/api/generated/schema'

export type NodeOut = components['schemas']['NodeResponses']

const nodeKeys = {
  list: (projectId: number, surveyId: number, versionNumber: number) =>
    ['nodes', 'project', projectId, 'survey', surveyId, 'version', versionNumber] as const,
}

export function useSurveyNodes(
  projectId: number | null,
  surveyId: number | null,
  versionNumber: number | null,
) {
  return useQuery({
    queryKey: nodeKeys.list(projectId ?? 0, surveyId ?? 0, versionNumber ?? 0),
    enabled: projectId != null && projectId > 0 && surveyId != null && surveyId > 0 && versionNumber != null && versionNumber > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/nodes',
        { params: { path: { project_id: projectId!, survey_id: surveyId!, version_number: versionNumber! } } },
      )
      if (error) throw error
      return data
    },
    staleTime: STALE.ACTIVE,
  })
}

export function useCreateNode(
  projectId: number | null,
  surveyId: number | null,
  versionNumber: number | null,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: components['schemas']['CreateNodeRequest']) => {
      if (projectId == null || surveyId == null || versionNumber == null) {
        throw new Error('projectId, surveyId and versionNumber are required')
      }
      const { data, error } = await apiClient.POST(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/nodes',
        { params: { path: { project_id: projectId, survey_id: surveyId, version_number: versionNumber } }, body },
      )
      if (error) throw error
      return data
    },
    onSuccess: () => {
      if (projectId != null && surveyId != null && versionNumber != null) {
        void queryClient.invalidateQueries({ queryKey: nodeKeys.list(projectId, surveyId, versionNumber) })
      }
    },
  })
}

export function useUpdateNode(
  projectId: number | null,
  surveyId: number | null,
  versionNumber: number | null,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      nodeId,
      body,
    }: {
      nodeId: number
      body: components['schemas']['UpdateNodeRequest']
    }) => {
      if (projectId == null || surveyId == null || versionNumber == null) {
        throw new Error('projectId, surveyId and versionNumber are required')
      }
      const { data, error } = await apiClient.PATCH(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/nodes/{node_id}',
        { params: { path: { project_id: projectId, survey_id: surveyId, version_number: versionNumber, node_id: nodeId } }, body },
      )
      if (error) throw error
      return data
    },
    onSuccess: () => {
      if (projectId != null && surveyId != null && versionNumber != null) {
        void queryClient.invalidateQueries({ queryKey: nodeKeys.list(projectId, surveyId, versionNumber) })
      }
    },
  })
}

export function useDeleteNode(
  projectId: number | null,
  surveyId: number | null,
  versionNumber: number | null,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (nodeId: number) => {
      if (projectId == null || surveyId == null || versionNumber == null) {
        throw new Error('projectId, surveyId and versionNumber are required')
      }
      const { error } = await apiClient.DELETE(
        '/api/v1/projects/{project_id}/surveys/{survey_id}/versions/{version_number}/nodes/{node_id}',
        { params: { path: { project_id: projectId, survey_id: surveyId, version_number: versionNumber, node_id: nodeId } } },
      )
      if (error) throw error
    },
    onSuccess: () => {
      if (projectId != null && surveyId != null && versionNumber != null) {
        void queryClient.invalidateQueries({ queryKey: nodeKeys.list(projectId, surveyId, versionNumber) })
      }
    },
  })
}
