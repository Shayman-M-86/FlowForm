import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isDesignPreviewMode } from '../../designPreview'
import { createMockProject, getMockProject, mockProjects } from '../../mockData'
import { useOpenApiClient } from '../../openapi'
import { createProject, deleteProject, getProject, getProjects, updateProject } from './requests'
import type { CreateProjectRequest, ProjectOut, UpdateProjectRequest } from './types'

export const projectKeys = {
  all: () => ['projects'] as const,
  list: () => [...projectKeys.all(), 'list'] as const,
  detail: (ref: string | number | null) => [...projectKeys.all(), 'detail', ref] as const,
}

export function useProjects() {
  const apiClient = useOpenApiClient()

  return useQuery({
    queryKey: projectKeys.list(),
    queryFn: () => (isDesignPreviewMode ? Promise.resolve([...mockProjects]) : getProjects(apiClient)),
  })
}

export function useProject(ref: string | number | null) {
  const apiClient = useOpenApiClient()

  return useQuery({
    queryKey: projectKeys.detail(ref),
    queryFn: () => {
      if (ref === null) throw new Error('Project ref is required')
      return isDesignPreviewMode ? Promise.resolve(getMockProject(ref)) : getProject(apiClient, ref)
    },
    enabled: ref !== null,
  })
}

export function useCreateProject() {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: CreateProjectRequest) =>
      isDesignPreviewMode ? Promise.resolve(createMockProject(body)) : createProject(apiClient, body),
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

export function useUpdateProject(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: UpdateProjectRequest) => updateProject(apiClient, projectId, body),
    onSuccess: (updated) => {
      queryClient.setQueryData<ProjectOut>(projectKeys.detail(updated.slug), updated)
      queryClient.setQueryData<ProjectOut[]>(projectKeys.list(), (current) =>
        current?.map((p) => (p.id === updated.id ? updated : p)),
      )
    },
  })
}

export function useDeleteProject() {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()
  const projects = queryClient.getQueryData<ProjectOut[]>(projectKeys.list())

  return useMutation({
    mutationFn: (ref: string | number) =>
      isDesignPreviewMode ? Promise.resolve() : deleteProject(apiClient, ref, projects),
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
