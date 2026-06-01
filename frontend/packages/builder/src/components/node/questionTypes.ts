/**
 * Re-exports the generated API types from @flowform/schema and provides
 * builder-local aliases and helpers used across question components.
 */

export type {
  ChoiceOptionIn as ChoiceOption,
  ChoiceDefinitionIn as ChoiceDefinition,
  ChoiceQuestionSchemaIn as ChoiceContent,
  MatchingItemIn as MatchingPrompt,
  MatchingItemIn as MatchingMatch,
  MatchingDefinitionIn as MatchingDefinition,
  MatchingQuestionSchemaIn as MatchingContent,
  RatingSliderDefinitionIn as RatingSliderDefinition,
  RatingEmojiDefinitionIn as RatingEmojiDefinition,
  RatingStarDefinitionIn as RatingStarDefinition,
  RatingQuestionSchemaIn as RatingContent,
  FieldDefinitionIn as FieldDefinition,
  FieldUIIn as FieldUI,
  FieldQuestionSchemaIn as FieldContent,
  ChoiceRequirementsIn as ChoiceRequirements,
  MatchingPairIn as MatchingPair,
  MatchingRequirementsIn as MatchingRequirements,
  RatingRequirementsIn as RatingRequirements,
  NumberFieldRequirementsIn as FieldNumberRequirements,
  DateFieldRequirementsIn as FieldDateRequirements,
  ChoiceConditionIn as ChoiceCondition,
  MatchingConditionIn as MatchingCondition,
  RatingConditionIn as RatingCondition,
  FieldConditionIn as FieldCondition,
  RuleSetItemIn as RuleSetEntry,
  SkipToActionIn as SkipToAction,
  EndAndSubmitActionIn as EndAndSubmitAction,
  EndAndDiscardActionIn as EndAndDiscardAction,
  RuleBranchIn as RuleBranch,
  RuleSchemaIn as RuleContent,
  RuleIfIn as RuleIf,
  CreateQuestionNodeRequest as QuestionNode,
  CreateRuleNodeRequest as RuleNode,
} from "@flowform/schema";

import type {
  ChoiceQuestionSchemaIn,
  MatchingQuestionSchemaIn,
  RatingQuestionSchemaIn,
  FieldQuestionSchemaIn,
  ChoiceConditionIn,
  MatchingConditionIn,
  RatingConditionIn,
  FieldConditionIn,
  NumberFieldRequirementsIn,
  DateFieldRequirementsIn,
  CreateQuestionNodeRequest,
  CreateRuleNodeRequest,
} from "@flowform/schema";

export type QuestionFamily = "choice" | "matching" | "rating" | "field";

export type RatingVariant = "slider" | "emoji" | "stars";

export type EmojiListType = "sad_to_happy" | "angry_to_happy" | "disgust_to_happy";

export type FieldType = "short_text" | "long_text" | "email" | "phone" | "number" | "date";

export type FieldNumberOperator = NumberFieldRequirementsIn["operator"];

export type FieldDateOperator = DateFieldRequirementsIn["operator"];

export type RuleMatch = "ALL" | "ANY" | "NONE";

export type QuestionContent =
  | ChoiceQuestionSchemaIn
  | MatchingQuestionSchemaIn
  | RatingQuestionSchemaIn
  | FieldQuestionSchemaIn;

export type RuleCondition =
  | ChoiceConditionIn
  | MatchingConditionIn
  | RatingConditionIn
  | FieldConditionIn;

export type RuleDoAction =
  | { skip_to: string }
  | { end_and_submit: true }
  | { end_and_discard: true };

export type SurveyNode = CreateQuestionNodeRequest | CreateRuleNodeRequest;

/* ---------- Narrowing helpers ------------------------------------------- */

export function isChoiceContent(content: QuestionContent): content is ChoiceQuestionSchemaIn {
  return content.family === "choice";
}

export function isMatchingContent(content: QuestionContent): content is MatchingQuestionSchemaIn {
  return content.family === "matching";
}

export function isRatingContent(content: QuestionContent): content is RatingQuestionSchemaIn {
  return content.family === "rating";
}

export function isFieldContent(content: QuestionContent): content is FieldQuestionSchemaIn {
  return content.family === "field";
}
