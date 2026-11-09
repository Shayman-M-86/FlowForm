import type { Attributes } from '@opentelemetry/api'

// Browser resource timing for traced API calls. The API sends
// Timing-Allow-Origin, so cross-origin entries carry DNS, connect, TLS and
// protocol details instead of zeros. The CORS preflight has no entry of its
// own; it falls between the connection becoming ready and requestStart.

type Waiter = {
  url: string
  after: number
  resolve: (entry: PerformanceResourceTiming | undefined) => void
}

const waiters = new Set<Waiter>()
let observer: PerformanceObserver | undefined

function ensureObserver(): boolean {
  if (observer) return true
  if (typeof PerformanceObserver === 'undefined') return false
  try {
    observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries() as PerformanceResourceTiming[]) {
        for (const waiter of waiters) {
          if (waiter.url === entry.name && entry.startTime >= waiter.after) {
            waiters.delete(waiter)
            waiter.resolve(entry)
            break
          }
        }
      }
    })
    observer.observe({ type: 'resource' })
    return true
  } catch {
    observer = undefined
    return false
  }
}

/**
 * Resolve with the resource timing entry for `url` that started at or after
 * `after` (a performance.now() value). Entries arrive once the response body
 * has been read, so callers must not block the response on this.
 */
export function waitForResourceTiming(
  url: string,
  after: number,
  timeoutMs = 5000,
): Promise<PerformanceResourceTiming | undefined> {
  if (!ensureObserver()) return Promise.resolve(undefined)
  return new Promise((resolve) => {
    const waiter: Waiter = { url, after, resolve }
    waiters.add(waiter)
    setTimeout(() => {
      if (waiters.delete(waiter)) resolve(undefined)
    }, timeoutMs)
  })
}

const PROTOCOL_VERSIONS: Record<string, string> = { h3: '3', h2: '2', 'http/1.1': '1.1', 'http/1.0': '1.0' }

function duration(start: number, end: number): number | undefined {
  return start > 0 && end >= start ? Math.round((end - start) * 10) / 10 : undefined
}

/** Span attributes describing where a request's browser-side time went. */
export function resourceTimingAttributes(t: PerformanceResourceTiming): Attributes {
  const connectionReady = Math.max(t.connectEnd, t.domainLookupEnd, t.fetchStart)
  const attributes: Attributes = {
    'network.protocol.version': PROTOCOL_VERSIONS[t.nextHopProtocol] ?? (t.nextHopProtocol || undefined),
    'flowform.timing.dns_ms': duration(t.domainLookupStart, t.domainLookupEnd),
    'flowform.timing.connect_ms': duration(t.connectStart, t.connectEnd),
    'flowform.timing.tls_ms': duration(t.secureConnectionStart, t.connectEnd),
    // Preflight round trip and browser queueing before the real request.
    'flowform.timing.preflight_or_queue_ms': duration(connectionReady, t.requestStart),
    'flowform.timing.ttfb_ms': duration(t.requestStart, t.responseStart),
    'flowform.timing.download_ms': duration(t.responseStart, t.responseEnd),
  }
  if (t.requestStart > 0) {
    attributes['flowform.timing.connection_reused'] = t.connectStart === t.connectEnd
  }
  return Object.fromEntries(Object.entries(attributes).filter(([, value]) => value !== undefined))
}
