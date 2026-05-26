import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isDesignPreviewMode } from '../../designPreview'
import { createMockProject, getMockProject, mockProjects } from '../../mockData'
import { useOpenApiClient } from '../../openapi'
import { loadCachedQuery, loadCachedQueryUpdatedAt, saveCachedQuery } from '../../queryStorage'
import { createProject, deleteProject, getProject, getProjects, updateProject } from './requests'
import type { CreateProjectRequest, ProjectOut, UpdateProjectRequest } from './types'

const FIVE_MINUTES = 5 * 60 * 1000

export const projectKeys = {
  all: () => ['projects'] as const,
  list: () => [...projectKeys.all(), 'list'] as const,
  detail: (ref: string | number | null) => [...projectKeys.all(), 'detail', ref] as const,
}

export function useProjects() {
  const apiClient = useOpenApiClient()
  const queryKey = projectKeys.list()

  return useQuery({
    queryKey,
    queryFn: async () => {
      const projects = isDesignPreviewMode ? [...mockProjects] : await getProjects(apiClient)
      if (!isDesignPreviewMode) saveCachedQuery(queryKey, projects)
      return projects
    },
    staleTime: FIVE_MINUTES,
    initialData: isDesignPreviewMode ? undefined : loadCachedQuery<ProjectOut[]>(queryKey, FIVE_MINUTES),
    initialDataUpdatedAt: () => isDesignPreviewMode ? undefined : loadCachedQueryUpdatedAt(queryKey),
  })
}

export function useProject(ref: string | number | null) {
  const apiClient = useOpenApiClient()
  const queryKey = projectKeys.detail(ref)

  return useQuery({
    queryKey,
    queryFn: async () => {
      if (ref === null) throw new Error('Project ref is required')
      const project = isDesignPreviewMode ? getMockProject(ref) : await getProject(apiClient, ref)
      if (!isDesignPreviewMode) saveCachedQuery(queryKey, project)
      return project
    },
    enabled: ref !== null,
    staleTime: FIVE_MINUTES,
    initialData: ref !== null && !isDesignPreviewMode ? loadCachedQuery<ProjectOut>(queryKey, FIVE_MINUTES) : undefined,
    initialDataUpdatedAt: () => ref !== null && !isDesignPreviewMode ? loadCachedQueryUpdatedAt(queryKey) : undefined,
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
