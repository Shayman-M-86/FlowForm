/**
 * Re-exports the generated API types from @flowform/schema and provides the
 * builder-local aliases and unions used across the question/rule components.
 */

export type {
  ChoiceQuestionSchemaIn as ChoiceContent,
  MatchingQuestionSchemaIn as MatchingContent,
  RatingQuestionSchemaIn as RatingContent,
  FieldQuestionSchemaIn as FieldContent,
  ChoiceRequirementsIn as ChoiceRequirements,
  MatchingRequirementsIn as MatchingRequirements,
  RatingRequirementsIn as RatingRequirements,
  RuleSetItemIn as RuleSetEntry,
  RuleBranchIn as RuleBranch,
  RuleSchemaIn as RuleContent,
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
  FieldDefinitionIn,
  RatingEmojiDefinitionIn,
  RuleIfIn,
  NumberFieldRequirementsIn,
  DateFieldRequirementsIn,
  CreateQuestionNodeRequest,
  CreateRuleNodeRequest,
} from "@flowform/schema";

export type EmojiListType = RatingEmojiDefinitionIn["emoji_list"];

export type FieldType = FieldDefinitionIn["field_type"];

export type FieldNumberOperator = NumberFieldRequirementsIn["operator"];

export type FieldDateOperator = DateFieldRequirementsIn["operator"];

export type RuleMatch = RuleIfIn["match"];

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

export type SurveyNode = CreateQuestionNodeRequest | CreateRuleNodeRequest;
