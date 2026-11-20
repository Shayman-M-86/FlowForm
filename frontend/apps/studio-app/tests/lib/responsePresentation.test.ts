import { describe, expect, it } from 'vitest'
import type { AnswerSlot } from '@/api/hooks/results'
import { presentAnswer } from '@/lib/responsePresentation'

const fieldUuid = '11111111-1111-4111-8111-111111111111'
const optionUuid = '22222222-2222-4222-8222-222222222222'
const choiceSpec = { type: 'choice', required: true } as const
const choiceField: NonNullable<AnswerSlot['field']> = {
  id: 'q1',
  uuid: fieldUuid,
  prompt: 'When do you drink coffee?',
  description: null,
  behaviour: null,
  interaction: {
    kind: 'single_choice',
    presentation: 'radio',
    options: [{ id: 'morning', uuid: optionUuid, label: 'In the morning' }],
  },
  answerSpec: choiceSpec,
}

function answer(overrides: Partial<AnswerSlot> = {}): AnswerSlot {
  return {
    field_uuid: fieldUuid,
    field_id: choiceField.id,
    has_encrypted_answer: true,
    decrypted: true,
    state: 'answered',
    answer_spec: choiceSpec,
    answer_value: optionUuid,
    field: choiceField,
    ...overrides,
  }
}

describe('response presentation', () => {
  it('uses the field prompt and option UUID labels from the pinned definition', () => {
    const presented = presentAnswer(answer())
    expect(presented.question).toBe('When do you drink coffee?')
    expect(presented.lines).toEqual(['In the morning'])

    const choiceSetSpec = { type: 'choice_set', required: true, constraints: null } as const
    expect(presentAnswer(answer({
      answer_spec: choiceSetSpec,
      answer_value: [optionUuid],
      field: {
        ...choiceField,
        answerSpec: choiceSetSpec,
        interaction: {
          kind: 'multiple_choice',
          presentation: 'checkboxes',
          options: [{ id: 'morning', uuid: optionUuid, label: 'In the morning' }],
        },
      },
    })).lines).toEqual(['In the morning'])
  })

  it('formats matching pairs, rating bounds, and scalar values', () => {
    expect(presentAnswer(answer({
      field: null,
      answer_spec: { type: 'object', valueType: 'matching', required: false },
      answer_value: { pairs: [{ prompt_uuid: fieldUuid, match_uuid: optionUuid }] },
    })).lines).toEqual([`${fieldUuid} → ${optionUuid}`])

    const ratingSpec = { type: 'integer', required: true, constraints: { min: 1, max: 5 } } as const
    expect(presentAnswer(answer({
      answer_spec: ratingSpec,
      answer_value: 3,
      field: {
        ...choiceField,
        prompt: 'How rested?',
        interaction: { kind: 'rating', presentation: 'stars', prefix: null, suffix: null },
        answerSpec: ratingSpec,
      },
    })).lines).toEqual(['3 of 5 stars'])

    expect(presentAnswer(answer({
      field: null,
      answer_spec: { type: 'boolean', required: false },
      answer_value: false,
    })).lines).toEqual(['No'])
    expect(presentAnswer(answer({
      field: null,
      answer_spec: { type: 'string', required: false, constraints: null },
      answer_value: 'I sleep well.',
    })).lines).toEqual(['I sleep well.'])
  })

  it('shows the saved states and falls back to the readable field ID when metadata is missing', () => {
    const unavailable = presentAnswer(answer({ field: null, decrypted: false, answer_value: null }))
    expect(unavailable.question).toBe('q1')
    expect(unavailable.lines).toEqual(['Answer unavailable'])
    expect(presentAnswer(answer({ state: 'cleared', answer_value: null })).lines).toEqual(['Answer cleared'])
  })
})
