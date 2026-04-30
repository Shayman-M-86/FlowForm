import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
    queryFn: () => fetchProjects(executor),
  })
}

export function useProject(ref: string | number | null) {
  const { executor } = useApi()
  return useQuery({
    queryKey: projectKeys.detail(ref),
    queryFn: () => {
      if (ref === null) throw new Error('Project ref is required')
      return fetchProject(executor, ref)
    },
    enabled: ref !== null,
  })
}

export function useCreateProject() {
  const { executor } = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateProjectRequest) => createProject(executor, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.list() })
    },
  })
}

export function useDeleteProject() {
  const { executor } = useApi()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (ref: string | number) => deleteProject(executor, ref),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.list() })
    },
  })
}
