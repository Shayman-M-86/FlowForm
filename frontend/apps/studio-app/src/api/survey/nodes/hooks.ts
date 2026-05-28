import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOpenApiClient } from '../../openapi'
import { createNode, deleteNode, listNodes, updateNode } from './requests'
import type { CreateNodeRequest, NodeOut, UpdateNodeRequest } from './types'

export const surveyNodeKeys = {
  all: () => ['survey-nodes'] as const,
  list: (projectId: number, surveyId: number, versionNumber: number) =>
    [...surveyNodeKeys.all(), 'list', projectId, surveyId, versionNumber] as const,
}

export function useSurveyNodes(projectId: number, surveyId: number, versionNumber: number) {
  const apiClient = useOpenApiClient()
  return useQuery({
    queryKey: surveyNodeKeys.list(projectId, surveyId, versionNumber),
    queryFn: () => listNodes(apiClient, projectId, surveyId, versionNumber),
    enabled: projectId > 0 && surveyId > 0 && versionNumber > 0,
  })
}

export function useCreateNode(projectId: number, surveyId: number, versionNumber: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateNodeRequest) =>
      createNode(apiClient, projectId, surveyId, versionNumber, body),
    onSuccess: (node) => {
      const key = surveyNodeKeys.list(projectId, surveyId, versionNumber)
      queryClient.setQueryData<NodeOut[]>(key, (current) =>
        current ? [...current, node] : [node],
      )
    },
  })
}

export function useUpdateNode(projectId: number, surveyId: number, versionNumber: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ nodeId, body }: { nodeId: number; body: UpdateNodeRequest }) =>
      updateNode(apiClient, projectId, surveyId, versionNumber, nodeId, body),
    onSuccess: (node) => {
      const key = surveyNodeKeys.list(projectId, surveyId, versionNumber)
      queryClient.setQueryData<NodeOut[]>(key, (current) =>
        current?.map((n) => (n.id === node.id ? node : n)),
      )
    },
  })
}

export function useDeleteNode(projectId: number, surveyId: number, versionNumber: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (nodeId: number) =>
      deleteNode(apiClient, projectId, surveyId, versionNumber, nodeId),
    onSuccess: (_, nodeId) => {
      const key = surveyNodeKeys.list(projectId, surveyId, versionNumber)
      queryClient.setQueryData<NodeOut[]>(key, (current) =>
        current?.filter((n) => n.id !== nodeId),
      )
    },
  })
}
