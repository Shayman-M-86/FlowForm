import type { AnswerSlot } from '@/api/hooks/results'

type JsonRecord = Record<string, unknown>

export type PresentedAnswer = {
  question: string
  section: string | null
  family: string | null
  lines: string[]
  hint: string | null
}

function record(value: unknown): JsonRecord | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as JsonRecord : null
}

function text(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null
}

function number(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function labelById(items: unknown, id: unknown): string {
  if (!Array.isArray(items)) return String(id)
  const match = items.find((item) => record(item)?.id === id)
  return text(record(match)?.label) ?? String(id)
}

function answerLines(answer: AnswerSlot, definition: JsonRecord | null): { lines: string[]; hint: string | null } {
  if (answer.state === 'cleared') return { lines: ['Answer cleared'], hint: null }
  if (!answer.decrypted) {
    return { lines: [answer.has_encrypted_answer ? 'Answer unavailable' : 'No answer recorded'], hint: null }
  }

  const value = record(answer.answer_value)
  if (!value) return { lines: ['No answer recorded'], hint: null }

  if (answer.answer_family === 'choice' && Array.isArray(value.selected)) {
    const labels = value.selected.map((id) => labelById(definition?.options, id))
    return { lines: labels.length ? labels : ['No option selected'], hint: null }
  }

  if (answer.answer_family === 'field') {
    const fieldType = text(value.field_type)
    const fieldValue = fieldType ? value[fieldType === 'short_text' || fieldType === 'long_text' ? 'text' : fieldType] : null
    if (typeof fieldValue === 'string' || typeof fieldValue === 'number') {
      return { lines: [String(fieldValue)], hint: null }
    }
  }

  if (answer.answer_family === 'matching' && Array.isArray(value.pairs)) {
    const pairs = value.pairs.map((pair) => {
      const ids = record(pair)
      if (!ids) return null
      return `${labelById(definition?.prompts, ids.prompt_id)} → ${labelById(definition?.matches, ids.match_id)}`
    }).filter((pair): pair is string => pair !== null)
    return { lines: pairs.length ? pairs : ['No matches recorded'], hint: null }
  }

  if (answer.answer_family === 'rating') {
    const rating = number(value.number)
    if (rating !== null) {
      const variant = text(value.variant)
      const stars = number(definition?.stars)
      const range = record(definition?.range)
      const ui = record(definition?.ui)
      const left = text(ui?.left_label)
      const right = text(ui?.right_label)
      const hint = left && right ? `${left} → ${right}` : null
      if (variant === 'stars') return { lines: [`${rating} of ${stars ?? 5} stars`], hint }
      if (variant === 'slider' && number(range?.min) !== null && number(range?.max) !== null) {
        return { lines: [`${rating} on a ${range?.min}–${range?.max} scale`], hint }
      }
      if (variant === 'emoji') return { lines: [`${rating} of 5`], hint }
      return { lines: [String(rating)], hint }
    }
  }

  return { lines: [JSON.stringify(value)], hint: 'Stored answer format could not be interpreted.' }
}

const FAMILY_LABELS: Record<string, string> = {
  choice: 'Choice',
  field: 'Text or field',
  matching: 'Matching',
  rating: 'Rating',
}

export function presentAnswer(answer: AnswerSlot): PresentedAnswer {
  const content = record(answer.question_content)
  const definition = record(content?.definition)
  const formatted = answerLines(answer, definition)
  return {
    question: text(content?.label) ?? 'Question wording unavailable',
    section: text(content?.title),
    family: answer.answer_family ? (FAMILY_LABELS[answer.answer_family] ?? answer.answer_family) : null,
    lines: formatted.lines,
    hint: formatted.hint,
  }
}

export function orderAnswers(answers: AnswerSlot[]): AnswerSlot[] {
  return [...answers].sort((left, right) =>
    (left.question_sort_key ?? Number.MAX_SAFE_INTEGER) - (right.question_sort_key ?? Number.MAX_SAFE_INTEGER),
  )
}
