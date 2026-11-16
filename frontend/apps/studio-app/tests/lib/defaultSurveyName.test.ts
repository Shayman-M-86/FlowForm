import { describe, expect, it } from 'vitest'
import { nameTakenIn, nextAvailableName, nextDefaultSurveyName } from '@/lib/surveyNames'

describe('default survey name', () => {
  it('uses "My survey" when it is free', () => {
    expect(nextDefaultSurveyName([])).toBe('My survey')
    expect(nextDefaultSurveyName([{ title: 'Sleep study' }])).toBe('My survey')
  })

  it('numbers the name when it is taken, ignoring case', () => {
    expect(nextDefaultSurveyName([{ title: 'my survey' }])).toBe('My survey 1')
    expect(nextDefaultSurveyName([{ title: 'My survey' }, { title: 'My Survey 1' }])).toBe('My survey 2')
  })

  it('skips names whose URL-safe form is already used', () => {
    expect(nextDefaultSurveyName([{ title: 'Other', public_slug: 'my-survey' }])).toBe('My survey 1')
  })
})

describe('next available name', () => {
  it('numbers link names per base, ignoring case', () => {
    expect(nextAvailableName('General Link', nameTakenIn([]))).toBe('General Link')
    expect(nextAvailableName('General Link', nameTakenIn(['general link', 'Private Invite Link']))).toBe('General Link 1')
    expect(nextAvailableName('General Link', nameTakenIn(['General Link', 'General Link 1']))).toBe('General Link 2')
  })
})
