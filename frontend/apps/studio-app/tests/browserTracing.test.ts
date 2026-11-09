import { afterEach, expect, it, vi } from 'vitest'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

it('propagates and exports only the Studio API span without request or page data', async () => {
  const collector = 'https://faro.example.test/collect/studio'
  vi.stubEnv('VITE_FARO_URL', collector)
  vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test')
  vi.stubEnv('VITE_DEPLOYMENT_ENVIRONMENT', 'staging')

  const send = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 200 }))
  vi.stubGlobal('fetch', send)

  const { tracedApiFetch } = await import('../src/api/browserTracing')
  const unrelated = new Request('https://other.example.test/api/token')
  await tracedApiFetch(unrelated)
  expect(unrelated.headers.has('traceparent')).toBe(false)

  const request = new Request('https://api.example.test/api/private-path?secret=query-token', {
    method: 'POST',
    headers: { Authorization: 'Bearer access-token' },
    body: 'response-data',
  })
  expect((await tracedApiFetch(request)).status).toBe(200)
  const parent = request.headers.get('traceparent')
  expect(parent).toMatch(/^00-[\da-f]{32}-[\da-f]{16}-01$/)

  await vi.waitFor(() => expect(send.mock.calls.some(([url]) => url === collector)).toBe(true), {
    timeout: 3500,
  })
  const [, options] = send.mock.calls.find(([url]) => url === collector)!
  expect(new Headers(options?.headers).get('x-faro-session-id')).toBeTruthy()
  const payload = String(options?.body)
  expect(payload).toContain(parent!.split('-')[1])
  expect(payload).toContain('flowform-studio-browser')
  expect(payload).not.toMatch(/private-path|query-token|access-token|response-data|"page"|"user"/)
})
