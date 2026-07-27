import { describe, expect, it } from 'vitest'
import {
  SURVEY_ACCESS_ENTRIES,
  SURVEY_ACCESS_MODES,
} from '@/lib/surveyAccessDesign'

describe('survey access design', () => {
  it('allows both assigned link types for private surveys', () => {
    expect(SURVEY_ACCESS_MODES.private.allowedEntries).toEqual([
      'private_invite_link',
      'authenticated_assigned_link',
    ])
    expect(SURVEY_ACCESS_MODES.private.blockedEntries).toEqual([
      'general_link',
      'public_slug',
    ])
  })

  it('does not present general links as authenticated links', () => {
    expect(SURVEY_ACCESS_ENTRIES.general_link.details).toContain(
      'Does not require sign-in',
    )
  })
})
