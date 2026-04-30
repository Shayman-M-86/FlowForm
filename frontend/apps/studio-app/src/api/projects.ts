import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useApi } from './useApi'
import type { ProjectOut, CreateProjectRequest } from './types'
import type { ApiExecutor } from './types'

// ── Query key factory ─────────────────────────────────────────────────────────

export const projectKeys = {
  all: () => ['projects'] as const,
  list: () => [...projectKeys.all(), 'list'] as const,
  detail: (id: number) => [...projectKeys.all(), 'detail', id] as const,
}

// ── Fetchers ──────────────────────────────────────────────────────────────────

function fetchProjects(executor: ApiExecutor): Promise<ProjectOut[]> {
  return executor.get('/api/v1/projects')
}

function fetchProject(executor: ApiExecutor, id: number): Promise<ProjectOut> {
  return executor.get(`/api/v1/projects/${id}`)
}

function createProject(executor: ApiExecutor, body: CreateProjectRequest): Promise<ProjectOut> {
  return executor.post('/api/v1/projects', body)
}

function deleteProject(executor: ApiExecutor, id: number): Promise<void> {
  return executor.del(`/api/v1/projects/${id}`)
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useProjects() {
  const { executor } = useApi()
  return useQuery({
    queryKey: projectKeys.list(),
    queryFn: () => fetchProjects(executor),
  })
}

export function useProject(id: number) {
  const { executor } = useApi()
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: () => fetchProject(executor, id),
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
    mutationFn: (id: number) => deleteProject(executor, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.list() })
    },
  })
}
