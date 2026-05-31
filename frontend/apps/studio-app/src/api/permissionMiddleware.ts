import type { Middleware } from 'openapi-fetch'
import type { QueryClient } from '@tanstack/react-query'
import { routePermissions } from './generated/rbac.gen'
import { permissionKeys } from './project/permissions/hooks'

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
          // If survey cache is populated, use it; otherwise fall through to project cache
          if (surveyPerms !== undefined) {
            if (!surveyPerms.includes(entry.permission)) {
              throw new PermissionDeniedError(entry.permission, pathname)
            }
            return undefined
          }
        }

        // Fall back to project-level permissions (covers all survey perms too)
        if (!projectPerms.includes(entry.permission)) {
          throw new PermissionDeniedError(entry.permission, pathname)
        }

        return undefined
      }

      return undefined
    },
  }
}
