import type { Middleware } from 'openapi-fetch'
import type { QueryClient } from '@tanstack/react-query'
import { routePermissions } from '../generated/rbac.gen'
import { permissionKeys } from '../hooks/permissions/queryKeys'

import { createStorageCooldown } from '@/lib/storageCooldown'

const permissionCooldown = createStorageCooldown({
  storageKey: 'flowform.perm-cooldowns',
  cooldownMs: 60_000,
})

function invalidateWithCooldown(queryClient: QueryClient, queryKey: readonly unknown[]) {
  permissionCooldown.attempt(JSON.stringify(queryKey), () => {
    void queryClient.invalidateQueries({ queryKey })
  })
}

export class PermissionDeniedError extends Error {
  public readonly permission: string
  public readonly url: string

  constructor(permission: string, url: string) {
    super(`Permission denied: ${permission} required for ${url}`)
    this.name = 'PermissionDeniedError'
    this.permission = permission
    this.url = url
  }
}

export function createPermissionMiddleware(queryClient: QueryClient): Middleware {
  return {
    onResponse({ response, request }) {
      if (response.status === 403) {
        const url = new URL(request.url)
        const pathname = url.pathname

        for (const entry of routePermissions) {
          if (entry.method !== request.method) continue
          const match = pathname.match(entry.pattern)
          if (!match?.groups) continue

          const projectIdStr = match.groups['project_id']
          const projectId = projectIdStr ? parseInt(projectIdStr, 10) : null
          if (projectId === null || isNaN(projectId)) continue

          const surveyIdStr = match.groups['survey_id']
          const surveyId = surveyIdStr ? parseInt(surveyIdStr, 10) : null

          if (surveyId !== null) {
            invalidateWithCooldown(queryClient, permissionKeys.survey(projectId, surveyId))
          }
          invalidateWithCooldown(queryClient, permissionKeys.project(projectId))
          break
        }
      }
      return response
    },

    onRequest({ request }) {
      const url = new URL(request.url)
      const pathname = url.pathname

      for (const entry of routePermissions) {
        if (entry.method !== request.method) continue
        const match = pathname.match(entry.pattern)
        if (!match?.groups) continue

        // Extract project_id from URL — required to look up the cache key
        const projectIdStr = match.groups['project_id']
        const projectId = projectIdStr ? parseInt(projectIdStr, 10) : null
        if (projectId === null || isNaN(projectId)) continue

        const surveyIdStr = match.groups['survey_id']
        const surveyId = surveyIdStr ? parseInt(surveyIdStr, 10) : null

        // Read from cache only — never trigger a fetch here
        const projectPerms = queryClient.getQueryData<string[]>(
          permissionKeys.project(projectId),
        )

        // Cold start: cache empty, let the request through (server will 403 if needed)
        if (projectPerms === undefined) return undefined

        // Check survey-scoped cache first if we have a survey_id and it's a survey permission
        if (surveyId !== null) {
          const surveyPerms = queryClient.getQueryData<string[]>(
            permissionKeys.survey(projectId, surveyId),
          )
          if (surveyPerms !== undefined) {
            if (!surveyPerms.includes(entry.permission)) {
              invalidateWithCooldown(queryClient, permissionKeys.survey(projectId, surveyId))
              throw new PermissionDeniedError(entry.permission, pathname)
            }
            return undefined
          }
        }

        // Fall back to project-level permissions (covers all survey perms too)
        if (!projectPerms.includes(entry.permission)) {
          invalidateWithCooldown(queryClient, permissionKeys.project(projectId))
          throw new PermissionDeniedError(entry.permission, pathname)
        }

        return undefined
      }

      return undefined
    },
  }
}
