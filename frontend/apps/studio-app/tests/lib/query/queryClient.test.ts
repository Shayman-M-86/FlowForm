import { describe, it, expect } from 'vitest'
import { queryClient } from '@/lib/query/queryClient'

// Extract the retry function from the queryClient default options
const retryFn = queryClient.getDefaultOptions().queries?.retry

if (typeof retryFn !== 'function') {
  throw new Error('Expected queryClient retry to be a function')
}

function apiError(code: string): Error {
  return Object.assign(new Error(code), { code })
}

describe('queryClient retry policy', () => {
  it('does not retry a RATE_LIMIT_EXCEEDED error', () => {
    const error = apiError('RATE_LIMIT_EXCEEDED')
    expect(retryFn(0, error)).toBe(false)
    expect(retryFn(1, error)).toBe(false)
  })

  it('retries other errors once (failureCount 0 → true)', () => {
    expect(retryFn(0, apiError('NOT_FOUND'))).toBe(true)
  })

  it('does not retry other errors a second time (failureCount 1 → false)', () => {
    expect(retryFn(1, apiError('SERVER_ERROR'))).toBe(false)
  })

  it('does not retry when error has no code', () => {
    expect(retryFn(0, new Error('unknown'))).toBe(true)
    expect(retryFn(1, new Error('unknown'))).toBe(false)
  })
})
