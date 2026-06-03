import { describe, it, expect, beforeEach, vi } from 'vitest'
import { QueryClient } from '@tanstack/react-query'
import { createPermissionMiddleware, PermissionDeniedError } from '@/api/middleware/permissionMiddleware'
import { permissionKeys } from '@/api/hooks/permissions/queryKeys'

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeRequest(method: string, pathname: string): Request {
  return new Request(`http://localhost:5000${pathname}`, { method })
}

function makeResponse(status: number): Response {
  return new Response(null, { status })
}

/** Call onRequest and return the result (or the thrown error). */
function callOnRequest(
  middleware: ReturnType<typeof createPermissionMiddleware>,
  request: Request,
): Request | Response | undefined | PermissionDeniedError {
  try {
    return (middleware as unknown as { onRequest: (ctx: { request: Request }) => unknown })
      .onRequest({ request }) as Request | Response | undefined
  } catch (e) {
    return e as PermissionDeniedError
  }
}

/** Call onResponse and return the response. */
function callOnResponse(
  middleware: ReturnType<typeof createPermissionMiddleware>,
  request: Request,
  response: Response,
): Response {
  return (middleware as unknown as { onResponse: (ctx: { request: Request; response: Response }) => Response })
    .onResponse({ request, response })
}

// ── Setup ─────────────────────────────────────────────────────────────────────

let queryClient: QueryClient
let middleware: ReturnType<typeof createPermissionMiddleware>

const PROJECT_ID = 5
const SURVEY_ID = 10

beforeEach(() => {
  localStorage.clear()
  vi.useRealTimers()
  queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  middleware = createPermissionMiddleware(queryClient)
})

// ── onRequest: cold cache ─────────────────────────────────────────────────────

describe('onRequest — cold cache', () => {
  it('lets the request through when no permission data is cached', () => {
    const req = makeRequest('GET', `/api/v1/projects/${PROJECT_ID}/surveys`)
    const result = callOnRequest(middleware, req)
    expect(result).toBeUndefined()
  })

  it('lets the request through for unrecognised paths', () => {
    queryClient.setQueryData(permissionKeys.project(PROJECT_ID), ['survey:view'])
    const req = makeRequest('GET', '/api/v1/me/profile')
    const result = callOnRequest(middleware, req)
    expect(result).toBeUndefined()
  })
})

// ── onRequest: project-level permission check ─────────────────────────────────

describe('onRequest — project-level permissions', () => {
  it('lets the request through when the permission is present', () => {
    queryClient.setQueryData(permissionKeys.project(PROJECT_ID), ['survey:view', 'survey:edit'])
    const req = makeRequest('GET', `/api/v1/projects/${PROJECT_ID}/surveys`)
    const result = callOnRequest(middleware, req)
    expect(result).toBeUndefined()
  })

  it('throws PermissionDeniedError when the permission is absent', () => {
    queryClient.setQueryData(permissionKeys.project(PROJECT_ID), ['survey:view'])
    const req = makeRequest('PATCH', `/api/v1/projects/${PROJECT_ID}/surveys/${SURVEY_ID}`)
    const result = callOnRequest(middleware, req)
    expect(result).toBeInstanceOf(PermissionDeniedError)
    expect((result as PermissionDeniedError).permission).toBe('survey:edit')
  })

  it('invalidates the project permission cache when blocking a request', () => {
    const spy = vi.spyOn(queryClient, 'invalidateQueries')
    queryClient.setQueryData(permissionKeys.project(PROJECT_ID), [])
    const req = makeRequest('DELETE', `/api/v1/projects/${PROJECT_ID}`)
    callOnRequest(middleware, req)
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: permissionKeys.project(PROJECT_ID) }),
    )
  })
})

// ── onRequest: survey-level permission check ──────────────────────────────────

describe('onRequest — survey-level permissions', () => {
  it('uses survey-scoped cache when available and allows the request', () => {
    queryClient.setQueryData(permissionKeys.project(PROJECT_ID), [])
    queryClient.setQueryData(permissionKeys.survey(PROJECT_ID, SURVEY_ID), ['survey:view'])
    const req = makeRequest('GET', `/api/v1/projects/${PROJECT_ID}/surveys/${SURVEY_ID}`)
    const result = callOnRequest(middleware, req)
    expect(result).toBeUndefined()
  })

  it('blocks and throws using survey-scoped cache when permission is absent', () => {
    queryClient.setQueryData(permissionKeys.project(PROJECT_ID), ['survey:view'])
    queryClient.setQueryData(permissionKeys.survey(PROJECT_ID, SURVEY_ID), [])
    const req = makeRequest('GET', `/api/v1/projects/${PROJECT_ID}/surveys/${SURVEY_ID}`)
    const result = callOnRequest(middleware, req)
    expect(result).toBeInstanceOf(PermissionDeniedError)
  })

  it('falls back to project-level cache when survey cache is absent', () => {
    queryClient.setQueryData(permissionKeys.project(PROJECT_ID), ['survey:view'])
    // no survey-level cache set
    const req = makeRequest('GET', `/api/v1/projects/${PROJECT_ID}/surveys/${SURVEY_ID}`)
    const result = callOnRequest(middleware, req)
    expect(result).toBeUndefined()
  })

  it('invalidates the survey permission cache when blocking via survey-scoped check', () => {
    const spy = vi.spyOn(queryClient, 'invalidateQueries')
    queryClient.setQueryData(permissionKeys.project(PROJECT_ID), ['survey:edit'])
    queryClient.setQueryData(permissionKeys.survey(PROJECT_ID, SURVEY_ID), [])
    const req = makeRequest('PATCH', `/api/v1/projects/${PROJECT_ID}/surveys/${SURVEY_ID}`)
    callOnRequest(middleware, req)
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: permissionKeys.survey(PROJECT_ID, SURVEY_ID) }),
    )
  })
})

// ── onRequest: cooldown prevents repeated invalidation ───────────────────────

describe('onRequest — cooldown', () => {
  it('does not invalidate again within the cooldown window', () => {
    const spy = vi.spyOn(queryClient, 'invalidateQueries')
    queryClient.setQueryData(permissionKeys.project(PROJECT_ID), [])

    const req = makeRequest('DELETE', `/api/v1/projects/${PROJECT_ID}`)
    callOnRequest(middleware, req)
    callOnRequest(middleware, req)
    callOnRequest(middleware, req)

    expect(spy).toHaveBeenCalledTimes(1)
  })

  it('allows re-invalidation after the cooldown expires', () => {
    vi.useFakeTimers()
    const spy = vi.spyOn(queryClient, 'invalidateQueries')
    queryClient.setQueryData(permissionKeys.project(PROJECT_ID), [])

    const req = makeRequest('DELETE', `/api/v1/projects/${PROJECT_ID}`)
    callOnRequest(middleware, req)
    expect(spy).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(60_001)

    callOnRequest(middleware, req)
    expect(spy).toHaveBeenCalledTimes(2)
  })
})

// ── onResponse: 403 handling ──────────────────────────────────────────────────

describe('onResponse — 403', () => {
  it('invalidates project permission cache on a 403 for a project-level route', () => {
    const spy = vi.spyOn(queryClient, 'invalidateQueries')
    const req = makeRequest('DELETE', `/api/v1/projects/${PROJECT_ID}`)
    callOnResponse(middleware, req, makeResponse(403))
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: permissionKeys.project(PROJECT_ID) }),
    )
  })

  it('invalidates both survey and project caches on a 403 for a survey-level route', () => {
    const spy = vi.spyOn(queryClient, 'invalidateQueries')
    const req = makeRequest('PATCH', `/api/v1/projects/${PROJECT_ID}/surveys/${SURVEY_ID}`)
    callOnResponse(middleware, req, makeResponse(403))

    const keys = spy.mock.calls.map((c) => JSON.stringify((c[0] as { queryKey: unknown }).queryKey))
    expect(keys).toContain(JSON.stringify(permissionKeys.survey(PROJECT_ID, SURVEY_ID)))
    expect(keys).toContain(JSON.stringify(permissionKeys.project(PROJECT_ID)))
  })

  it('returns the 403 response unchanged', () => {
    const req = makeRequest('DELETE', `/api/v1/projects/${PROJECT_ID}`)
    const res = makeResponse(403)
    const returned = callOnResponse(middleware, req, res)
    expect(returned).toBe(res)
  })

  it('does not invalidate on a 200 response', () => {
    const spy = vi.spyOn(queryClient, 'invalidateQueries')
    const req = makeRequest('GET', `/api/v1/projects/${PROJECT_ID}/surveys`)
    callOnResponse(middleware, req, makeResponse(200))
    expect(spy).not.toHaveBeenCalled()
  })

  it('does not invalidate again within the cooldown window on repeated 403s', () => {
    const spy = vi.spyOn(queryClient, 'invalidateQueries')
    const req = makeRequest('DELETE', `/api/v1/projects/${PROJECT_ID}`)
    callOnResponse(middleware, req, makeResponse(403))
    callOnResponse(middleware, req, makeResponse(403))
    callOnResponse(middleware, req, makeResponse(403))
    // project-level: 1 call; no survey_id so only project
    expect(spy).toHaveBeenCalledTimes(1)
  })
})

// ── PermissionDeniedError shape ───────────────────────────────────────────────

describe('PermissionDeniedError', () => {
  it('carries the permission and url that were denied', () => {
    const err = new PermissionDeniedError('survey:edit', '/api/v1/projects/5/surveys/10')
    expect(err.permission).toBe('survey:edit')
    expect(err.url).toBe('/api/v1/projects/5/surveys/10')
    expect(err.name).toBe('PermissionDeniedError')
    expect(err).toBeInstanceOf(Error)
  })
})
