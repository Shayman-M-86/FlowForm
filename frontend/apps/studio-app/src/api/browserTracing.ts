import { SpanKind, SpanStatusCode } from '@opentelemetry/api'
import { resourceTimingAttributes, waitForResourceTiming } from './resourceTiming'

const collectorUrl = import.meta.env.VITE_FARO_URL as string | undefined
const apiUrl = import.meta.env.VITE_API_BASE_URL as string | undefined

async function initializeTracer(url: string) {
  const [{ initializeFaro, SessionInstrumentation, TransportItemType }, { TracingInstrumentation }] =
    await Promise.all([import('@grafana/faro-web-sdk'), import('@grafana/faro-web-tracing')])

  const faro = initializeFaro({
    url,
    app: {
      name: 'flowform-studio-browser',
      environment: import.meta.env.VITE_DEPLOYMENT_ENVIRONMENT || import.meta.env.MODE,
    },
    instrumentations: [
      new SessionInstrumentation(),
      new TracingInstrumentation({ instrumentations: [] }),
    ],
    beforeSend(item) {
      // Send only spans from the API client, with no page URL or user metadata.
      if (item.type !== TransportItemType.TRACE) return null
      return { ...item, meta: { app: item.meta.app, sdk: item.meta.sdk, session: item.meta.session } }
    },
  })

  return faro.api.getOTEL()?.trace.getTracer('flowform-studio-browser')
}

let tracer: ReturnType<typeof initializeTracer> | undefined

export async function tracedApiFetch(request: Request, init?: RequestInit): Promise<Response> {
  if (!collectorUrl || !apiUrl || typeof window === 'undefined') return fetch(request, init)

  const target = new URL(request.url)
  if (target.origin !== new URL(apiUrl, window.location.origin).origin || !target.pathname.startsWith('/api/')) {
    return fetch(request, init)
  }

  tracer ??= initializeTracer(collectorUrl).catch(() => undefined)
  const span = (await tracer)?.startSpan(`HTTP ${request.method}`, {
    kind: SpanKind.CLIENT,
    attributes: { 'http.request.method': request.method, 'server.address': target.hostname },
  })
  if (!span?.isRecording()) return fetch(request, init)

  const { traceId, spanId, traceFlags } = span.spanContext()
  const startedAt = performance.now()
  const timing = waitForResourceTiming(request.url, startedAt - 1)
  try {
    request.headers.set('traceparent', `00-${traceId}-${spanId}-${traceFlags.toString(16).padStart(2, '0')}`)
    const response = await fetch(request, init)
    span.setAttribute('http.response.status_code', response.status)
    if (!response.ok) span.setStatus({ code: SpanStatusCode.ERROR })
    return response
  } catch (error) {
    span.setStatus({ code: SpanStatusCode.ERROR })
    throw error
  } finally {
    // The span ends when the response headers arrived; the timing entry only
    // appears after the caller reads the body, so attach it before ending.
    const endedAt = performance.timeOrigin + performance.now()
    void timing.then((entry) => {
      if (entry) span.setAttributes(resourceTimingAttributes(entry))
      span.end(endedAt)
    })
  }
}
