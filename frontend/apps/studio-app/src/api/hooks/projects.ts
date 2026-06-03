import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { STALE } from '@/lib/query/queryClient'
import type { components } from '@/api/generated/schema'

export type Project = components['schemas']['ProjectResponses']

const projectKeys = {
  all: () => ['projects'] as const,
  bySlug: (slug: string) => ['projects', 'slug', slug] as const,
  byId: (id: number) => ['projects', 'id', id] as const,
}

export function useProjects() {
  return useQuery({
    queryKey: projectKeys.all(),
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/projects')
      if (error) throw error
      return data
    },
    staleTime: STALE.SLOW,
    meta: { persist: 'local' },
  })
}

/**
 * Look up a project by slug. The backend exposes GET by project_id only,
 * so we derive the result from the project list query. slug=null disables
 * the query without error.
 */
export function useProject(slug: string | null) {
  const list = useProjects()
  const project = slug != null ? list.data?.find((p) => p.slug === slug) : undefined

  return {
    ...list,
    data: project,
  }
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: components['schemas']['CreateProjectRequest']) => {
      const { data, error } = await apiClient.POST('/api/v1/projects', { body })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all() })
    },
  })
}

export function useUpdateProject(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: components['schemas']['UpdateProjectRequest']) => {
      const { data, error } = await apiClient.PATCH('/api/v1/projects/{project_id}', {
        params: { path: { project_id: projectId } },
        body,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all() })
    },
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (projectId: number) => {
      const { error } = await apiClient.DELETE('/api/v1/projects/{project_id}', {
        params: { path: { project_id: projectId } },
      })
      if (error) throw error
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.all() })
    },
  })
}
