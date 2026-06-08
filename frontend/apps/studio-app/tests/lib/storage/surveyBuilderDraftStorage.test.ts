import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { SurveyNode } from '@flowform/builder'
import {
  clearSurveyBuilderDraft,
  loadSurveyBuilderDraft,
  saveSurveyBuilderDraft,
  surveyBuilderDraftKey,
} from '@/lib/storage'

const PROJECT_ID = 12
const SURVEY_ID = 34
const VERSION_ID = 56

const nodes: SurveyNode[] = [{
  id: 1,
  node_key: 'q1',
  node_type: 'question',
  sort_key: 100000,
  content: {
    family: 'field',
    label: 'Name',
    title: null,
    definition: {
      field_type: 'short_text',
      ui: { placeholder: 'Type your name' },
    },
  },
}]

beforeEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
})

describe('survey builder draft storage', () => {
  it('builds a version-scoped recovery key', () => {
    expect(surveyBuilderDraftKey(PROJECT_ID, SURVEY_ID, VERSION_ID)).toBe(
      'flowform.survey-builder.draft.v1:12:34:56',
    )
  })

  it('saves and loads draft recovery nodes', () => {
    saveSurveyBuilderDraft(PROJECT_ID, SURVEY_ID, VERSION_ID, nodes)

    const recovered = loadSurveyBuilderDraft(PROJECT_ID, SURVEY_ID, VERSION_ID)
    expect(recovered?.nodes).toEqual(nodes)
    expect(typeof recovered?.savedAt).toBe('number')
  })

  it('clears a saved draft', () => {
    saveSurveyBuilderDraft(PROJECT_ID, SURVEY_ID, VERSION_ID, nodes)
    clearSurveyBuilderDraft(PROJECT_ID, SURVEY_ID, VERSION_ID)

    expect(loadSurveyBuilderDraft(PROJECT_ID, SURVEY_ID, VERSION_ID)).toBeNull()
  })

  it('ignores corrupted draft data', () => {
    localStorage.setItem(surveyBuilderDraftKey(PROJECT_ID, SURVEY_ID, VERSION_ID), 'not json{{')

    expect(loadSurveyBuilderDraft(PROJECT_ID, SURVEY_ID, VERSION_ID)).toBeNull()
  })

  it('guards against storage write failures', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage full')
    })

    expect(() => saveSurveyBuilderDraft(PROJECT_ID, SURVEY_ID, VERSION_ID, nodes)).not.toThrow()
  })
})
