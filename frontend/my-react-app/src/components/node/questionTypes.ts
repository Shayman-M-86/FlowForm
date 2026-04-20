/**
 * Shared types for survey question cards.
 *
 * Card components own their `content`: every card's `getData()` returns a
 * `QuestionContent` in the shape the spec expects. The page (orchestrator)
 * wraps that content with `{ type: "question", sort_key, content }` when
 * serializing — cards never produce the envelope themselves.
 */

export type QuestionFamily = "choice" | "matching" | "rating" | "field";

/* ---------- Choice ------------------------------------------------------- */

export interface ChoiceOption {
  id: string;
  label: string;
}

export interface ChoiceDefinition {
  min: number;
  max: number;
  options: ChoiceOption[];
}

export interface ChoiceContent {
  id: string;
  title: string;
  label: string;
  family: "choice";
  definition: ChoiceDefinition;
}

/* ---------- Matching ----------------------------------------------------- */

export interface MatchingPrompt {
  id: string;
  label: string;
}

export interface MatchingMatch {
  id: string;
  label: string;
}

export interface MatchingDefinition {
  prompts: MatchingPrompt[];
  matches: MatchingMatch[];
}

export interface MatchingContent {
  id: string;
  title: string;
  label: string;
  family: "matching";
  definition: MatchingDefinition;
}

/* ---------- Rating ------------------------------------------------------- */

export type RatingVariant = "slider" | "emoji" | "star";

export type EmojiListType = "sad_to_happy" | "angry_to_happy" | "disgust_to_happy";

export interface RatingSliderDefinition {
  variant: "slider";
  range: {
    min: number;
    max: number;
    step: number;
  };
  ui: {
    left_label: string;
    right_label: string;
  };
}

export interface RatingEmojiDefinition {
  variant: "emoji";
  emoji_list: EmojiListType;
  words: boolean;
  ui: {
    left_label: string;
    right_label: string;
  };
}

export interface RatingStarDefinition {
  variant: "star";
  stars: number;
  ui: {
    left_label: string;
    right_label: string;
  };
}

export type RatingDefinition =
  | RatingSliderDefinition
  | RatingEmojiDefinition
  | RatingStarDefinition;

export interface RatingContent {
  id: string;
  title: string;
  label: string;
  family: "rating";
  definition: RatingDefinition;
}

/* ---------- Field -------------------------------------------------------- */

export type FieldType = "short_text" | "long_text" | "email" | "phone" | "number" | "date";

export interface FieldDefinition {
  field_type: FieldType;
  ui: {
    placeholder?: string;
  };
}

export interface FieldContent {
  id: string;
  title: string;
  label: string;
  family: "field";
  definition: FieldDefinition;
}

/* ---------- Union -------------------------------------------------------- */

export type QuestionContent =
  | ChoiceContent
  | MatchingContent
  | RatingContent
  | FieldContent;

/* ---------- Rules -------------------------------------------------------- */

export type RuleMatch = "ALL" | "ANY" | "NONE";

export interface ChoiceRequirements {
  required?: string[];
  forbidden?: string[];
  any_of?: string[];
}

export interface MatchingPair {
  [promptId: string]: string;
}

export interface MatchingRequirements {
  required?: MatchingPair[];
}

export interface RatingRequirements {
  min?: number;
  max?: number;
}

export type FieldNumberOperator = "LT" | "LTE" | "GT" | "GTE" | "EQ" | "NEQ";
export type FieldDateOperator = "before" | "after";

export interface FieldNumberRequirements {
  type: "short_text" | "long_text" | "email" | "phone" | "number";
  operator: FieldNumberOperator;
  value: number | string;
}

export interface FieldDateRequirements {
  type: "date";
  operator: FieldDateOperator;
  value: string;
}

export type FieldRequirements = FieldNumberRequirements | FieldDateRequirements;

export interface ChoiceCondition {
  target_id: string;
  family: "choice";
  requirements: ChoiceRequirements;
}

export interface MatchingCondition {
  target_id: string;
  family: "matching";
  requirements: MatchingRequirements;
}

export interface RatingCondition {
  target_id: string;
  family: "rating";
  requirements: RatingRequirements;
}

export interface FieldCondition {
  target_id: string;
  family: "field";
  requirements: FieldRequirements;
}

export type RuleCondition =
  | ChoiceCondition
  | MatchingCondition
  | RatingCondition
  | FieldCondition;

export interface RuleSetEntry {
  target_id: string;
  visible?: boolean;
  required?: boolean;
}

export type RuleDoAction =
  | { skip_to: string }
  | { end_and_submit: true }
  | { end_and_discard: true };

export interface RuleThen {
  set?: RuleSetEntry[];
  do?: RuleDoAction;
}

export interface RuleElse {
  do?: RuleDoAction;
}

export interface RuleContent {
  id: string;
  if: {
    match: RuleMatch;
    conditions: RuleCondition[];
  };
  then: RuleThen;
  else?: RuleElse;
}

/* ---------- Envelopes (owned by the page) ------------------------------- */

export interface QuestionNode {
  type: "question";
  sort_key: number;
  content: QuestionContent;
}

export interface RuleNode {
  type: "rule";
  sort_key: number;
  content: RuleContent;
}

export type SurveyNode = QuestionNode | RuleNode;

/* ---------- Narrowing helpers ------------------------------------------- */

export function isChoiceContent(content: QuestionContent): content is ChoiceContent {
  return content.family === "choice";
}

export function isMatchingContent(content: QuestionContent): content is MatchingContent {
  return content.family === "matching";
}

export function isRatingContent(content: QuestionContent): content is RatingContent {
  return content.family === "rating";
}

export function isFieldContent(content: QuestionContent): content is FieldContent {
  return content.family === "field";
}
