// This file is auto-generated — do not edit manually

// ──────────────────────────────────────────────────────────────────────────
// Requests
// ──────────────────────────────────────────────────────────────────────────

export const ChoiceRequirementsInConstraints = {
  required: { maxItems: 50 },
  forbidden: { maxItems: 50 },
  any_of: { maxItems: 50 },
} as const;

export const ChoiceConditionInConstraints = {
  target_id: { minLength: 1, maxLength: 128 },
  family: { maxLength: 6 },
} as const;

export const ChoiceOptionInConstraints = {
  id: { minLength: 1, maxLength: 128 },
  label: { minLength: 1, maxLength: 1000 },
} as const;

export const ChoiceDefinitionInConstraints = {
  min: { minimum: 0 },
  max: { minimum: 1 },
  options: { maxItems: 10 },
} as const;

export const ChoiceQuestionSchemaInConstraints = {
  family: { maxLength: 6 },
  label: { minLength: 1, maxLength: 1000 },
  title: { minLength: 0, maxLength: 500 },
} as const;

export const DateFieldRequirementsInConstraints = {
  type: { maxLength: 4 },
  operator: { maxLength: 6 },
  value: { maxLength: 10 },
} as const;

export const NumberFieldRequirementsInConstraints = {
  type: { maxLength: 6 },
  operator: { maxLength: 3 },
} as const;

export const FieldConditionInConstraints = {
  target_id: { minLength: 1, maxLength: 128 },
  family: { maxLength: 5 },
} as const;

export const FieldUIInConstraints = {
  placeholder: { maxLength: 50 },
} as const;

export const FieldDefinitionInConstraints = {
  field_type: { maxLength: 10 },
} as const;

export const FieldQuestionSchemaInConstraints = {
  family: { maxLength: 5 },
  label: { minLength: 1, maxLength: 1000 },
  title: { minLength: 0, maxLength: 500 },
} as const;

export const MatchingPairInConstraints = {
  prompt_id: { minLength: 1, maxLength: 128 },
  match_id: { minLength: 1, maxLength: 128 },
} as const;

export const MatchingRequirementsInConstraints = {
  required: { minItems: 1, maxItems: 50 },
} as const;

export const MatchingConditionInConstraints = {
  target_id: { minLength: 1, maxLength: 128 },
  family: { maxLength: 8 },
} as const;

export const MatchingItemInConstraints = {
  id: { minLength: 1, maxLength: 128 },
  label: { minLength: 1, maxLength: 250 },
} as const;

export const MatchingDefinitionInConstraints = {
  prompts: { maxItems: 10 },
  matches: { maxItems: 10 },
} as const;

export const MatchingQuestionSchemaInConstraints = {
  family: { maxLength: 8 },
  label: { minLength: 1, maxLength: 1000 },
  title: { minLength: 0, maxLength: 500 },
} as const;

export const RatingUIInConstraints = {
  left_label: { minLength: 1, maxLength: 50 },
  right_label: { minLength: 1, maxLength: 50 },
} as const;

export const RatingSliderDefinitionInConstraints = {
  variant: { maxLength: 6 },
} as const;

export const RatingStarDefinitionInConstraints = {
  variant: { maxLength: 5 },
  stars: { minimum: 1, maximum: 12 },
} as const;

export const RatingEmojiDefinitionInConstraints = {
  variant: { maxLength: 5 },
  emoji_list: { maxLength: 16 },
} as const;

export const RatingQuestionSchemaInConstraints = {
  family: { maxLength: 6 },
  label: { minLength: 1, maxLength: 1000 },
  title: { minLength: 0, maxLength: 500 },
} as const;

export const RatingConditionInConstraints = {
  target_id: { minLength: 1, maxLength: 128 },
  family: { maxLength: 6 },
} as const;

export const RuleSetItemInConstraints = {
  target_id: { minLength: 1, maxLength: 128 },
} as const;

export const SkipToActionInConstraints = {
  skip_to: { minLength: 1, maxLength: 128 },
} as const;

export const RuleBranchInConstraints = {
  set: { minItems: 1, maxItems: 50 },
} as const;

export const RuleIfInConstraints = {
  match: { maxLength: 4 },
  conditions: { minItems: 1, maxItems: 50 },
} as const;

export const CreateQuestionNodeRequestConstraints = {
  id: { maxLength: 36 },
  node_key: { minLength: 1, maxLength: 128 },
  node_type: { maxLength: 8 },
} as const;

export const CreateRuleNodeRequestConstraints = {
  id: { maxLength: 36 },
  node_key: { minLength: 1, maxLength: 128 },
  node_type: { maxLength: 4 },
} as const;
