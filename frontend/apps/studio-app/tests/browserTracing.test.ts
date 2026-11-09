import { afterEach, expect, it, vi } from 'vitest'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

const collector = 'https://faro.example.test/collect/studio'

function stubTracingEnv() {
  vi.stubEnv('VITE_FARO_URL', collector)
  vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test')
  vi.stubEnv('VITE_DEPLOYMENT_ENVIRONMENT', 'staging')
}

async function exportedPayload(send: ReturnType<typeof vi.fn<typeof fetch>>) {
  await vi.waitFor(() => expect(send.mock.calls.some(([url]) => url === collector)).toBe(true), {
    timeout: 3500,
  })
  const [, options] = send.mock.calls.find(([url]) => url === collector)!
  return { headers: new Headers(options?.headers), payload: String(options?.body) }
}

it('propagates and exports only the Studio API span without request or page data', async () => {
  stubTracingEnv()
  // No resource timing support: the span must still end and export.
  vi.stubGlobal('PerformanceObserver', undefined)

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

  const { headers, payload } = await exportedPayload(send)
  expect(headers.get('x-faro-session-id')).toBeTruthy()
  expect(payload).toContain(parent!.split('-')[1])
  expect(payload).toContain('flowform-studio-browser')
  expect(payload).not.toMatch(/private-path|query-token|access-token|response-data|"page"|"user"/)
})

// Faro is a page-wide singleton, so this test reuses the tracer initialised above.
it('adds browser resource timing to the API span', async () => {
  stubTracingEnv()
  const url = 'https://api.example.test/api/v1/example'
  let deliver: ((entries: unknown[]) => void) | undefined
  vi.stubGlobal(
    'PerformanceObserver',
    class {
      constructor(callback: (list: { getEntries: () => unknown[] }) => void) {
        deliver = (entries) => callback({ getEntries: () => entries })
      }
      observe() {}
    },
  )
  const send = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 200 }))
  vi.stubGlobal('fetch', send)

  const { tracedApiFetch } = await import('../src/api/browserTracing')
  await tracedApiFetch(new Request(url))
  deliver!([
    {
      name: url,
      startTime: performance.now(),
      nextHopProtocol: 'h3',
      fetchStart: 1,
      domainLookupStart: 1,
      domainLookupEnd: 1,
      connectStart: 1,
      secureConnectionStart: 0,
      connectEnd: 1,
      requestStart: 30,
      responseStart: 50,
      responseEnd: 51,
    },
  ])

  const { payload } = await exportedPayload(send)
  expect(payload).toContain('flowform.timing.preflight_or_queue_ms')
  expect(payload).toContain('flowform.timing.ttfb_ms')
})
