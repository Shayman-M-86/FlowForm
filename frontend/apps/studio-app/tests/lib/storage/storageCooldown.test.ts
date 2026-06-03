import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createStorageCooldown } from '@/lib/storage/storageCooldown'

const STORAGE_KEY = 'test.cooldowns'
const COOLDOWN_MS = 60_000

function makeCooldown() {
  return createStorageCooldown({ storageKey: STORAGE_KEY, cooldownMs: COOLDOWN_MS })
}

beforeEach(() => {
  localStorage.clear()
  vi.useRealTimers()
})

describe('createStorageCooldown', () => {
  describe('attempt', () => {
    it('fires the callback on first call', () => {
      const cooldown = makeCooldown()
      const fn = vi.fn()
      cooldown.attempt('key-a', fn)
      expect(fn).toHaveBeenCalledOnce()
    })

    it('blocks the callback within the cooldown window', () => {
      const cooldown = makeCooldown()
      const fn = vi.fn()
      cooldown.attempt('key-a', fn)
      cooldown.attempt('key-a', fn)
      cooldown.attempt('key-a', fn)
      expect(fn).toHaveBeenCalledOnce()
    })

    it('allows the callback again after the cooldown expires', () => {
      vi.useFakeTimers()
      const cooldown = makeCooldown()
      const fn = vi.fn()

      cooldown.attempt('key-a', fn)
      expect(fn).toHaveBeenCalledTimes(1)

      vi.advanceTimersByTime(COOLDOWN_MS + 1)

      cooldown.attempt('key-a', fn)
      expect(fn).toHaveBeenCalledTimes(2)
    })

    it('tracks different keys independently', () => {
      const cooldown = makeCooldown()
      const fn = vi.fn()

      cooldown.attempt('key-a', fn)
      cooldown.attempt('key-b', fn)

      expect(fn).toHaveBeenCalledTimes(2)

      cooldown.attempt('key-a', fn)
      cooldown.attempt('key-b', fn)

      expect(fn).toHaveBeenCalledTimes(2)
    })

    it('persists the cooldown across instances (simulating page refresh)', () => {
      const first = makeCooldown()
      const fn = vi.fn()
      first.attempt('key-a', fn)
      expect(fn).toHaveBeenCalledTimes(1)

      const second = makeCooldown()
      second.attempt('key-a', fn)
      expect(fn).toHaveBeenCalledTimes(1)
    })

    it('writes a timestamp to localStorage', () => {
      const cooldown = makeCooldown()
      const before = Date.now()
      cooldown.attempt('key-a', vi.fn())
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') as Record<string, number>
      expect(stored['key-a']).toBeGreaterThanOrEqual(before)
      expect(stored['key-a']).toBeLessThanOrEqual(Date.now())
    })
  })

  describe('isOnCooldown', () => {
    it('returns false when the key has never been used', () => {
      const cooldown = makeCooldown()
      expect(cooldown.isOnCooldown('never-used')).toBe(false)
    })

    it('returns true immediately after attempt', () => {
      const cooldown = makeCooldown()
      cooldown.attempt('key-a', vi.fn())
      expect(cooldown.isOnCooldown('key-a')).toBe(true)
    })

    it('returns false after the cooldown window expires', () => {
      vi.useFakeTimers()
      const cooldown = makeCooldown()
      cooldown.attempt('key-a', vi.fn())
      vi.advanceTimersByTime(COOLDOWN_MS + 1)
      expect(cooldown.isOnCooldown('key-a')).toBe(false)
    })
  })

  describe('resilience', () => {
    it('handles corrupted localStorage gracefully', () => {
      localStorage.setItem(STORAGE_KEY, 'not valid json{{')
      const cooldown = makeCooldown()
      const fn = vi.fn()
      expect(() => cooldown.attempt('key-a', fn)).not.toThrow()
      expect(fn).toHaveBeenCalledOnce()
    })

    it('handles localStorage.setItem throwing (e.g. storage full)', () => {
      vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new Error('QuotaExceededError')
      })
      const cooldown = makeCooldown()
      const fn = vi.fn()
      expect(() => cooldown.attempt('key-a', fn)).not.toThrow()
      expect(fn).toHaveBeenCalledOnce()
    })
  })
})
