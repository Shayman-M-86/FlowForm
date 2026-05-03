import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { isDesignPreviewMode } from './designPreview'
import { createMockProject, getMockProject, mockProjects } from './mockData'
import { useApi } from './useApi'
import type { ProjectOut, CreateProjectRequest } from './types'
import type { ApiExecutor } from './types'

// ── Query key factory ─────────────────────────────────────────────────────────

export const projectKeys = {
  all: () => ['projects'] as const,
  list: () => [...projectKeys.all(), 'list'] as const,
  detail: (ref: string | number | null) => [...projectKeys.all(), 'detail', ref] as const,
}

// ── Fetchers ──────────────────────────────────────────────────────────────────

function fetchProjects(executor: ApiExecutor): Promise<ProjectOut[]> {
  return executor.get('/api/v1/projects')
}

function fetchProject(executor: ApiExecutor, ref: string | number): Promise<ProjectOut> {
  return executor.get(`/api/v1/projects/${ref}`)
}

function createProject(executor: ApiExecutor, body: CreateProjectRequest): Promise<ProjectOut> {
  return executor.post('/api/v1/projects', body)
}

function deleteProject(executor: ApiExecutor, ref: string | number): Promise<void> {
  return executor.del(`/api/v1/projects/${ref}`)
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useProjects() {
  const { executor } = useApi()
  return useQuery({
    queryKey: projectKeys.list(),
    queryFn: () =>
      isDesignPreviewMode ? Promise.resolve([...mockProjects]) : fetchProjects(executor),
  })
}

export function useProject(ref: string | number | null) {
  const { executor } = useApi()
  return useQuery({
    queryKey: projectKeys.detail(ref),
    queryFn: () => {
      if (ref === null) throw new Error('Project ref is required')
      if (isDesignPreviewMode) return Promise.resolve(getMockProject(ref))
      return fetchProject(executor, ref)
    },
    enabled: ref !== null,
  })
}

export function useCreateProject() {
  const { executor } = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateProjectRequest) =>
      isDesignPreviewMode ? Promise.resolve(createMockProject(body)) : createProject(executor, body),
    onSuccess: (project) => {
      if (isDesignPreviewMode) {
        queryClient.setQueryData<ProjectOut[]>(projectKeys.list(), (current = mockProjects) => [
          project,
          ...current,
        ])
        queryClient.setQueryData(projectKeys.detail(project.slug), project)
        return
      }

      void queryClient.invalidateQueries({ queryKey: projectKeys.list() })
    },
  })
}

export function useDeleteProject() {
  const { executor } = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (ref: string | number) =>
      isDesignPreviewMode ? Promise.resolve() : deleteProject(executor, ref),
    onSuccess: (_result, ref) => {
      if (isDesignPreviewMode) {
        queryClient.setQueryData<ProjectOut[]>(projectKeys.list(), (current = mockProjects) =>
          current.filter((project) => project.id !== Number(ref) && project.slug !== String(ref)),
        )
        return
      }

      void queryClient.invalidateQueries({ queryKey: projectKeys.list() })
    },
  })
}
