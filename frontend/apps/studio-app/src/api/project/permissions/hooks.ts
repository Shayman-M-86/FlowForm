import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useOpenApiClient } from '../../openapi'
import { getMyProjectPermissions } from './requests'
import type { ProjectPermission } from './types'

const TEN_MINUTES = 10 * 60 * 1000

// Clear all cached permissions on every page load so a refresh always fetches
// fresh data. The localStorage entries are only used to seed the cache within
// the same JS session (navigation between routes), not across page loads.
export function clearAllCachedPermissions() {
  try {
    const toRemove = Object.keys(localStorage).filter((k) => k.startsWith('ff.permissions.'))
    toRemove.forEach((k) => localStorage.removeItem(k))
  } catch {
    // ignore
  }
}

export const permissionKeys = {
  all: () => ['permissions'] as const,
  project: (projectId: number) => [...permissionKeys.all(), 'project', projectId] as const,
}

function loadCachedPermissions(projectId: number): ProjectPermission[] | undefined {
  try {
    const raw = localStorage.getItem(`ff.permissions.project.${projectId}`)
    if (!raw) return undefined
    const { permissions, cachedAt } = JSON.parse(raw) as { permissions: ProjectPermission[]; cachedAt: number }
    if (Date.now() - cachedAt > TEN_MINUTES) return undefined
    return permissions
  } catch {
    return undefined
  }
}

function saveCachedPermissions(projectId: number, permissions: ProjectPermission[]) {
  try {
    localStorage.setItem(
      `ff.permissions.project.${projectId}`,
      JSON.stringify({ permissions, cachedAt: Date.now() }),
    )
  } catch {
    // storage quota exceeded — ignore
  }
}

export function useMyProjectPermissions(projectId: number | null) {
  const apiClient = useOpenApiClient()

  return useQuery({
    queryKey: permissionKeys.project(projectId ?? 0),
    queryFn: async () => {
      if (projectId === null) throw new Error('Project id required')
      const permissions = await getMyProjectPermissions(apiClient, projectId)
      saveCachedPermissions(projectId, permissions)
      return permissions
    },
    enabled: projectId !== null,
    staleTime: TEN_MINUTES,
    initialData: projectId !== null ? loadCachedPermissions(projectId) : undefined,
    initialDataUpdatedAt: () => {
      if (projectId === null) return undefined
      try {
        const raw = localStorage.getItem(`ff.permissions.project.${projectId}`)
        if (!raw) return undefined
        const { cachedAt } = JSON.parse(raw) as { cachedAt: number }
        return cachedAt
      } catch {
        return undefined
      }
    },
  })
}

export function useHasProjectPermission(projectId: number | null, permission: ProjectPermission): boolean {
  const { data } = useMyProjectPermissions(projectId)
  return data?.includes(permission) ?? false
}

export function useInvalidateProjectPermissions() {
  const queryClient = useQueryClient()
  return (projectId: number) => {
    localStorage.removeItem(`ff.permissions.project.${projectId}`)
    void queryClient.invalidateQueries({ queryKey: permissionKeys.project(projectId) })
  }
}
