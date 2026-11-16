import { describe, expect, it } from 'vitest'
import {
  LIVE_POLL_ACTIVE_MS,
  LIVE_POLL_IDLE_MS,
  liveResultsPollInterval,
  type SubjectTree,
} from '@/api/hooks/results'

function subjectWith(...statuses: Array<'completed' | 'in_progress' | 'abandoned'>): SubjectTree {
  return {
    sessions: statuses.map((status) => ({ session: { status } })),
  } as unknown as SubjectTree
}

describe('live results polling', () => {
  it('polls every second while any session is in progress', () => {
    const data = { items: [subjectWith('completed'), subjectWith('abandoned', 'in_progress')] }
    expect(liveResultsPollInterval(data)).toBe(LIVE_POLL_ACTIVE_MS)
    expect(LIVE_POLL_ACTIVE_MS).toBe(1_000)
  })

  it('polls every three seconds when nothing is in progress', () => {
    expect(liveResultsPollInterval({ items: [subjectWith('completed', 'abandoned')] })).toBe(LIVE_POLL_IDLE_MS)
    expect(liveResultsPollInterval({ items: [] })).toBe(LIVE_POLL_IDLE_MS)
    expect(liveResultsPollInterval(undefined)).toBe(LIVE_POLL_IDLE_MS)
    expect(LIVE_POLL_IDLE_MS).toBe(3_000)
  })
})
