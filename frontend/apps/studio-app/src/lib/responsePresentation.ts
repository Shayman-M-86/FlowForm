import type { AnswerSlot } from '@/api/hooks/results'

type Interaction = NonNullable<AnswerSlot['field']>['interaction']
type AnswerSpec = NonNullable<AnswerSlot['answer_spec']>

const INTERACTION_LABELS: Record<Interaction['kind'], string> = {
  short_text: 'Text',
  long_text: 'Text',
  number: 'Number',
  rating: 'Rating',
  single_choice: 'Choice',
  multiple_choice: 'Choice',
  boolean: 'Yes or no',
  date: 'Date',
}

const SPEC_LABELS: Record<AnswerSpec['type'], string> = {
  string: 'Text',
  number: 'Number',
  integer: 'Number',
  boolean: 'Yes or no',
  date: 'Date',
  choice: 'Choice',
  choice_set: 'Choice',
  object: 'Matching',
}

function optionLabel(interaction: Interaction | undefined, uuid: string): string {
  if (interaction?.kind !== 'single_choice' && interaction?.kind !== 'multiple_choice') return uuid
  return interaction.options.find((option) => option.uuid === uuid)?.label ?? uuid
}

function answerLines(answer: AnswerSlot): string[] {
  if (answer.state === 'cleared') return ['Answer cleared']
  if (!answer.decrypted) {
    return [answer.has_encrypted_answer ? 'Answer unavailable' : 'No answer recorded']
  }

  const { answer_value: value } = answer
  const interaction = answer.field?.interaction
  const spec = answer.answer_spec ?? answer.field?.answerSpec
  if (value === null) return ['No answer recorded']
  if (Array.isArray(value)) {
    return value.length ? value.map((uuid) => optionLabel(interaction, uuid)) : ['No option selected']
  }
  if (typeof value === 'object') {
    return value.pairs.length
      ? value.pairs.map(({ prompt_uuid, match_uuid }) => `${prompt_uuid} → ${match_uuid}`)
      : ['No matches recorded']
  }
  if (typeof value === 'boolean') return [value ? 'Yes' : 'No']
  if (typeof value === 'string' && spec?.type === 'choice') return [optionLabel(interaction, value)]
  if (
    typeof value === 'number' &&
    interaction?.kind === 'rating' &&
    (spec?.type === 'number' || spec?.type === 'integer')
  ) {
    const min = spec.constraints?.min
    const max = spec.constraints?.max
    if (interaction.presentation === 'stars' && max != null) return [`${value} of ${max} stars`]
    if (min != null && max != null) return [`${value} on a ${min}–${max} scale`]
  }
  return [String(value)]
}

export function presentAnswer(answer: AnswerSlot) {
  const field = answer.field
  const spec = answer.answer_spec ?? field?.answerSpec
  return {
    question: field?.prompt ?? answer.field_id ?? 'Question wording unavailable',
    description: field?.description ?? null,
    family: field ? INTERACTION_LABELS[field.interaction.kind] : spec ? SPEC_LABELS[spec.type] : null,
    lines: answerLines(answer),
  }
}
