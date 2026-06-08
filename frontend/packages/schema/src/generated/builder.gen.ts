// This file is auto-generated — do not edit manually

// ──────────────────────────────────────────────────────────────────────────
// Requests
// ──────────────────────────────────────────────────────────────────────────

export interface ChoiceRequirementsIn {
  required?: string[];
  forbidden?: string[];
  any_of?: string[];
}

export interface ChoiceConditionIn {
  target_id: string;
  family: "choice";
  requirements: ChoiceRequirementsIn;
}

export interface ChoiceOptionIn {
  id: string;
  label: string;
}

export interface ChoiceDefinitionIn {
  min: number;
  max: number;
  options: ChoiceOptionIn[];
}

export interface ChoiceQuestionSchemaIn {
  family: "choice";
  label: string;
  title?: string | null;
  definition: ChoiceDefinitionIn;
}

export interface DateFieldRequirementsIn {
  type: "date";
  operator: "before" | "after";
  value: string;
}

export interface EndAndDiscardActionIn {
  end_and_discard?: boolean;
}

export interface EndAndSubmitActionIn {
  end_and_submit?: boolean;
}

export interface NumberFieldRequirementsIn {
  type: "number";
  operator: "LT" | "LTE" | "GT" | "GTE" | "EQ" | "NEQ";
  value: number | number;
}

export interface FieldConditionIn {
  target_id: string;
  family: "field";
  requirements: NumberFieldRequirementsIn | DateFieldRequirementsIn;
}

export interface FieldUIIn {
  placeholder?: string;
}

export interface FieldDefinitionIn {
  field_type: "short_text" | "long_text" | "email" | "number" | "date" | "phone";
  ui?: FieldUIIn;
}

export interface FieldQuestionSchemaIn {
  family: "field";
  label: string;
  title?: string | null;
  definition: FieldDefinitionIn;
}

export interface MatchingPairIn {
  prompt_id: string;
  match_id: string;
}

export interface MatchingRequirementsIn {
  required: MatchingPairIn[];
}

export interface MatchingConditionIn {
  target_id: string;
  family: "matching";
  requirements: MatchingRequirementsIn;
}

export interface MatchingItemIn {
  id: string;
  label: string;
}

export interface MatchingDefinitionIn {
  prompts: MatchingItemIn[];
  matches: MatchingItemIn[];
}

export interface MatchingQuestionSchemaIn {
  family: "matching";
  label: string;
  title?: string | null;
  definition: MatchingDefinitionIn;
}

export interface RatingRangeIn {
  min: number | number;
  max: number | number;
  step: number | number;
}

export interface RatingUIIn {
  left_label: string;
  right_label: string;
}

export interface RatingSliderDefinitionIn {
  variant: "slider";
  range: RatingRangeIn;
  ui: RatingUIIn;
}

export interface RatingStarDefinitionIn {
  variant: "stars";
  stars: number;
  ui: RatingUIIn;
}

export interface RatingEmojiDefinitionIn {
  variant: "emoji";
  emoji_list: "sad_to_happy" | "angry_to_happy" | "disgust_to_happy";
  words?: boolean;
  ui: RatingUIIn;
}

export interface RatingQuestionSchemaIn {
  family: "rating";
  label: string;
  title?: string | null;
  definition: RatingSliderDefinitionIn | RatingStarDefinitionIn | RatingEmojiDefinitionIn;
}

export interface RatingRequirementsIn {
  min?: number | number | null;
  max?: number | number | null;
}

export interface RatingConditionIn {
  target_id: string;
  family: "rating";
  requirements: RatingRequirementsIn;
}

export interface RuleSetItemIn {
  target_id: string;
  visible?: boolean | null;
  required?: boolean | null;
}

export interface SkipToActionIn {
  skip_to: string;
}

export interface RuleBranchIn {
  set?: RuleSetItemIn[] | null;
  do?: SkipToActionIn | EndAndSubmitActionIn | EndAndDiscardActionIn | null;
}

export interface RuleIfIn {
  match: "ALL" | "ANY" | "NONE";
  conditions: (ChoiceConditionIn | MatchingConditionIn | RatingConditionIn | FieldConditionIn)[];
}

export interface RuleSchemaIn {
  if: RuleIfIn;
  then: RuleBranchIn;
  else?: RuleBranchIn | null;
}

export interface CreateQuestionNodeRequest {
  id: number;
  node_key: string;
  node_type: "question";
  sort_key: number;
  content: ChoiceQuestionSchemaIn | FieldQuestionSchemaIn | MatchingQuestionSchemaIn | RatingQuestionSchemaIn;
}

export interface CreateRuleNodeRequest {
  id: number;
  node_key: string;
  node_type: "rule";
  sort_key: number;
  content: RuleSchemaIn;
}
