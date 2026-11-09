import { describe, expect, it } from 'vitest'
import { resourceTimingAttributes } from '@/api/resourceTiming'

function entry(overrides: Partial<PerformanceResourceTiming>): PerformanceResourceTiming {
  return {
    nextHopProtocol: '',
    fetchStart: 0,
    domainLookupStart: 0,
    domainLookupEnd: 0,
    connectStart: 0,
    secureConnectionStart: 0,
    connectEnd: 0,
    requestStart: 0,
    responseStart: 0,
    responseEnd: 0,
    ...overrides,
  } as PerformanceResourceTiming
}

describe('resourceTimingAttributes', () => {
  it('splits a new HTTP/2 connection into DNS, connect, TLS, preflight and server time', () => {
    const attributes = resourceTimingAttributes(
      entry({
        nextHopProtocol: 'h2',
        fetchStart: 100,
        domainLookupStart: 100,
        domainLookupEnd: 110,
        connectStart: 110,
        secureConnectionStart: 200,
        connectEnd: 300,
        requestStart: 520,
        responseStart: 860,
        responseEnd: 861,
      }),
    )

    expect(attributes).toEqual({
      'network.protocol.version': '2',
      'flowform.timing.dns_ms': 10,
      'flowform.timing.connect_ms': 190,
      'flowform.timing.tls_ms': 100,
      'flowform.timing.preflight_or_queue_ms': 220,
      'flowform.timing.ttfb_ms': 340,
      'flowform.timing.download_ms': 1,
      'flowform.timing.connection_reused': false,
    })
  })

  it('marks a reused HTTP/3 connection', () => {
    const attributes = resourceTimingAttributes(
      entry({
        nextHopProtocol: 'h3',
        fetchStart: 50,
        domainLookupStart: 50,
        domainLookupEnd: 50,
        connectStart: 50,
        connectEnd: 50,
        requestStart: 51,
        responseStart: 80,
        responseEnd: 80.4,
      }),
    )

    expect(attributes['network.protocol.version']).toBe('3')
    expect(attributes['flowform.timing.connection_reused']).toBe(true)
    expect(attributes['flowform.timing.ttfb_ms']).toBe(29)
    expect(attributes).not.toHaveProperty('flowform.timing.tls_ms')
  })

  it('omits details the browser withholds without Timing-Allow-Origin', () => {
    expect(resourceTimingAttributes(entry({ fetchStart: 10, responseEnd: 90 }))).toEqual({})
  })
})
