// This file is auto-generated — do not edit manually

export const ChoiceOptionMapConfigConstraints = {
  combine: { maxLength: 3 },
} as const;

export const FieldNumericRangesConfigConstraints = {
  ranges: { maxItems: 50 },
} as const;

export const MatchingAnswerKeyConfigConstraints = {
  correct_pairs: { maxItems: 50 },
} as const;

export const ChoiceAnswerValueConstraints = {
  selected: { maxItems: 50 },
} as const;

export const FieldAnswerValueConstraints = {
  value: { maxLength: 5000 },
} as const;

export const MatchPairConstraints = {
  left_id: { maxLength: 128 },
  right_id: { maxLength: 128 },
} as const;

export const MatchingAnswerValueConstraints = {
  matches: { maxItems: 50 },
} as const;
