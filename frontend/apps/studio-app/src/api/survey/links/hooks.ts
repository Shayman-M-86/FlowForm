import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOpenApiClient } from '../../openapi'
import { loadCachedQuery, loadCachedQueryUpdatedAt, saveCachedQuery } from '../../queryStorage'
import { surveyKeys } from '../../project/surveys/hooks'
import { createPublicLink, deletePublicLink, getPublicLinks, updatePublicLink } from './requests'
import type { CreatePublicLinkRequest, PublicLinkOut, UpdatePublicLinkInput } from './types'

const ONE_MINUTE = 60 * 1000

export const linkKeys = {
  all: () => ['links'] as const,
  list: (projectId: number, surveyId: number) =>
    [...linkKeys.all(), 'list', projectId, surveyId] as const,
}

export function usePublicLinks(projectId: number, surveyId: number) {
  const apiClient = useOpenApiClient()
  const queryKey = linkKeys.list(projectId, surveyId)

  return useQuery({
    queryKey,
    queryFn: async () => {
      const links = await getPublicLinks(apiClient, projectId, surveyId)
      saveCachedQuery(queryKey, links)
      return links
    },
    enabled: projectId > 0 && surveyId > 0,
    staleTime: ONE_MINUTE,
    initialData: projectId > 0 && surveyId > 0
      ? loadCachedQuery<PublicLinkOut[]>(queryKey, ONE_MINUTE)
      : undefined,
    initialDataUpdatedAt: () => projectId > 0 && surveyId > 0 ? loadCachedQueryUpdatedAt(queryKey) : undefined,
  })
}

export function useCreatePublicLink(projectId: number, surveyId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: CreatePublicLinkRequest) =>
      createPublicLink(apiClient, projectId, surveyId, body),
    onSuccess: (link) => {
      const queryKey = linkKeys.list(projectId, surveyId)
      queryClient.setQueryData<PublicLinkOut[]>(queryKey, (current) => {
        const next = current ? [link, ...current] : [link]
        saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}

export function useUpdatePublicLink(projectId: number, surveyId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ linkId, body }: { linkId: number; body: UpdatePublicLinkInput }) =>
      updatePublicLink(apiClient, projectId, surveyId, linkId, body),
    onSuccess: (updated) => {
      const queryKey = linkKeys.list(projectId, surveyId)
      queryClient.setQueryData<PublicLinkOut[]>(queryKey, (current) => {
        const next = current?.map((l) => (l.id === updated.id ? updated : l))
        if (next) saveCachedQuery(queryKey, next)
        return next
      })
    },
  })
}

export function useDeletePublicLink(projectId: number, surveyId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (linkId: number) => deletePublicLink(apiClient, projectId, surveyId, linkId),
    onSuccess: (_result, linkId) => {
      const queryKey = linkKeys.list(projectId, surveyId)
      queryClient.setQueryData<PublicLinkOut[]>(queryKey, (current) => {
        const next = current?.filter((l) => l.id !== linkId)
        if (next) saveCachedQuery(queryKey, next)
        return next
      })
      void queryClient.invalidateQueries({ queryKey: surveyKeys.detail(projectId, surveyId) })
    },
  })
}
