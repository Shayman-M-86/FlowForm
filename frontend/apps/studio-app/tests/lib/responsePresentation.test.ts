import { describe, expect, it } from 'vitest'
import type { AnswerSlot } from '@/api/hooks/results'
import { orderAnswers, presentAnswer } from '@/lib/responsePresentation'

function answer(overrides: Partial<AnswerSlot>): AnswerSlot {
  return {
    question_node_id: '11111111-1111-4111-8111-111111111111',
    question_key: 'q1',
    answer_family: 'choice',
    has_encrypted_answer: true,
    decrypted: true,
    state: 'answered',
    answer_value: { selected: ['morning'] },
    question_content: {
      family: 'choice',
      label: 'When do you drink coffee?',
      definition: { min: 0, max: 1, options: [{ id: 'morning', label: 'In the morning' }] },
    },
    question_sort_key: 20,
    ...overrides,
  }
}

describe('response presentation', () => {
  it('uses the recorded question and option labels instead of IDs', () => {
    const presented = presentAnswer(answer({}))
    expect(presented.question).toBe('When do you drink coffee?')
    expect(presented.lines).toEqual(['In the morning'])
  })

  it('formats matching, rating, and field answers', () => {
    expect(presentAnswer(answer({
      answer_family: 'matching',
      answer_value: { pairs: [{ prompt_id: 'vic', match_id: 'au' }] },
      question_content: {
        family: 'matching', label: 'Match the state',
        definition: { prompts: [{ id: 'vic', label: 'Victoria' }], matches: [{ id: 'au', label: 'Australia' }] },
      },
    })).lines).toEqual(['Victoria → Australia'])

    expect(presentAnswer(answer({
      answer_family: 'rating',
      answer_value: { variant: 'stars', number: 3 },
      question_content: { family: 'rating', label: 'How rested?', definition: { variant: 'stars', stars: 5 } },
    })).lines).toEqual(['3 of 5 stars'])

    expect(presentAnswer(answer({
      answer_family: 'field',
      answer_value: { field_type: 'long_text', text: 'I sleep well.' },
      question_content: { family: 'field', label: 'Tell us more', definition: { field_type: 'long_text' } },
    })).lines).toEqual(['I sleep well.'])
  })

  it('shows a safe fallback and keeps historical question order', () => {
    expect(presentAnswer(answer({ decrypted: false, answer_value: null })).lines).toEqual(['Answer unavailable'])
    expect(orderAnswers([
      answer({ question_sort_key: 20 }),
      answer({ question_sort_key: 10 }),
    ]).map((item) => item.question_sort_key)).toEqual([10, 20])
  })
})
