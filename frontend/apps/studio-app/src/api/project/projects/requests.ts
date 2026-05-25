import type { OpenApiFetchClient } from '../../openapi'
import type { CreateProjectRequest, ProjectOut, UpdateProjectRequest } from './types'

function findProject(projects: ProjectOut[], ref: string | number): ProjectOut {
  const project = typeof ref === 'number'
    ? projects.find((item) => item.id === ref)
    : projects.find((item) => item.slug === ref)
  if (!project) throw new Error('Project not found')
  return project
}

export async function getProjects(apiClient: OpenApiFetchClient): Promise<ProjectOut[]> {
  const { data, error } = await apiClient.GET('/api/v1/projects')
  if (error) throw error
  return data
}

export async function getProject(
  apiClient: OpenApiFetchClient,
  ref: string | number,
): Promise<ProjectOut> {
  if (typeof ref === 'number') {
    const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}', {
      params: { path: { project_id: ref } },
    })
    if (error) throw error
    return data
  }

  return findProject(await getProjects(apiClient), ref)
}

export async function createProject(
  apiClient: OpenApiFetchClient,
  body: CreateProjectRequest,
): Promise<ProjectOut> {
  const { data, error } = await apiClient.POST('/api/v1/projects', { body })
  if (error) throw error
  return data
}

export async function updateProject(
  apiClient: OpenApiFetchClient,
  projectId: number,
  body: UpdateProjectRequest,
): Promise<ProjectOut> {
  const { data, error } = await apiClient.PATCH('/api/v1/projects/{project_id}', {
    params: { path: { project_id: projectId } },
    body,
  })
  if (error) throw error
  return data
}

export async function deleteProject(
  apiClient: OpenApiFetchClient,
  ref: string | number,
  projects: ProjectOut[] | undefined,
): Promise<void> {
  const projectId = toProjectId(ref, projects)
  const { error } = await apiClient.DELETE('/api/v1/projects/{project_id}', {
    params: { path: { project_id: projectId } },
  })
  if (error) throw error
}

export function toProjectId(ref: string | number, projects: ProjectOut[] | undefined): number {
  if (typeof ref === 'number') return ref

  const project = projects?.find((item) => item.slug === ref)
  if (project) return project.id

  const numericRef = Number(ref)
  if (Number.isInteger(numericRef)) return numericRef

  throw new Error('Project id is required')
}
