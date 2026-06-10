// This file is auto-generated — do not edit manually
import { z } from "zod";

// ──────────────────────────────────────────────────────────────────────────
// Requests
// ──────────────────────────────────────────────────────────────────────────

export const ChoiceRequirementsInSchema = z.object({
  required: z.array(z.string().min(1).max(128)).max(50).optional(),
  forbidden: z.array(z.string().min(1).max(128)).max(50).optional(),
  any_of: z.array(z.string().min(1).max(128)).max(50).optional(),
});

export const ChoiceConditionInSchema = z.object({
  target_id: z.string().min(1).max(128),
  family: z.literal("choice"),
  requirements: ChoiceRequirementsInSchema,
});

export const ChoiceOptionInSchema = z.object({
  id: z.string().min(1).max(128),
  label: z.string().min(1).max(1000),
});

export const ChoiceDefinitionInSchema = z.object({
  min: z.number().int().min(0),
  max: z.number().int().min(1),
  options: z.array(ChoiceOptionInSchema).max(10),
});

export const ChoiceQuestionSchemaInSchema = z.object({
  family: z.literal("choice"),
  label: z.string().min(1).max(1000),
  title: z.string().min(0).max(500).nullable().optional(),
  definition: ChoiceDefinitionInSchema,
});

export const DateFieldRequirementsInSchema = z.object({
  type: z.literal("date"),
  operator: z.enum(["before", "after"]),
  value: z.string().max(10),
});

export const EndAndDiscardActionInSchema = z.object({
  end_and_discard: z.boolean().optional(),
});

export const EndAndSubmitActionInSchema = z.object({
  end_and_submit: z.boolean().optional(),
});

export const NumberFieldRequirementsInSchema = z.object({
  type: z.literal("number"),
  operator: z.enum(["LT", "LTE", "GT", "GTE", "EQ", "NEQ"]),
  value: z.union([z.number().int(), z.number()]),
});

export const FieldConditionInSchema = z.object({
  target_id: z.string().min(1).max(128),
  family: z.literal("field"),
  requirements: z.discriminatedUnion("type", [NumberFieldRequirementsInSchema, DateFieldRequirementsInSchema]),
});

export const FieldUIInSchema = z.object({
  placeholder: z.string().max(50).optional(),
});

export const FieldDefinitionInSchema = z.object({
  field_type: z.enum(["short_text", "long_text", "email", "number", "date", "phone"]),
  ui: FieldUIInSchema.optional(),
});

export const FieldQuestionSchemaInSchema = z.object({
  family: z.literal("field"),
  label: z.string().min(1).max(1000),
  title: z.string().min(0).max(500).nullable().optional(),
  definition: FieldDefinitionInSchema,
});

export const MatchingPairInSchema = z.object({
  prompt_id: z.string().min(1).max(128),
  match_id: z.string().min(1).max(128),
});

export const MatchingRequirementsInSchema = z.object({
  required: z.array(MatchingPairInSchema).min(1).max(50),
});

export const MatchingConditionInSchema = z.object({
  target_id: z.string().min(1).max(128),
  family: z.literal("matching"),
  requirements: MatchingRequirementsInSchema,
});

export const MatchingItemInSchema = z.object({
  id: z.string().min(1).max(128),
  label: z.string().min(1).max(250),
});

export const MatchingDefinitionInSchema = z.object({
  prompts: z.array(MatchingItemInSchema).max(10),
  matches: z.array(MatchingItemInSchema).max(10),
});

export const MatchingQuestionSchemaInSchema = z.object({
  family: z.literal("matching"),
  label: z.string().min(1).max(1000),
  title: z.string().min(0).max(500).nullable().optional(),
  definition: MatchingDefinitionInSchema,
});

export const RatingRangeInSchema = z.object({
  min: z.union([z.number().int(), z.number()]),
  max: z.union([z.number().int(), z.number()]),
  step: z.union([z.number().int(), z.number()]),
});

export const RatingUIInSchema = z.object({
  left_label: z.string().min(1).max(50),
  right_label: z.string().min(1).max(50),
});

export const RatingSliderDefinitionInSchema = z.object({
  variant: z.literal("slider"),
  range: RatingRangeInSchema,
  ui: RatingUIInSchema,
});

export const RatingStarDefinitionInSchema = z.object({
  variant: z.literal("stars"),
  stars: z.number().int().min(1).max(12),
  ui: RatingUIInSchema,
});

export const RatingEmojiDefinitionInSchema = z.object({
  variant: z.literal("emoji"),
  emoji_list: z.enum(["sad_to_happy", "angry_to_happy", "disgust_to_happy"]),
  words: z.boolean().optional(),
  ui: RatingUIInSchema,
});

export const RatingQuestionSchemaInSchema = z.object({
  family: z.literal("rating"),
  label: z.string().min(1).max(1000),
  title: z.string().min(0).max(500).nullable().optional(),
  definition: z.discriminatedUnion("variant", [RatingSliderDefinitionInSchema, RatingStarDefinitionInSchema, RatingEmojiDefinitionInSchema]),
});

export const RatingRequirementsInSchema = z.object({
  min: z.union([z.number().int(), z.number()]).nullable().optional(),
  max: z.union([z.number().int(), z.number()]).nullable().optional(),
});

export const RatingConditionInSchema = z.object({
  target_id: z.string().min(1).max(128),
  family: z.literal("rating"),
  requirements: RatingRequirementsInSchema,
});

export const RuleSetItemInSchema = z.object({
  target_id: z.string().min(1).max(128),
  visible: z.boolean().nullable().optional(),
  required: z.boolean().nullable().optional(),
});

export const SkipToActionInSchema = z.object({
  skip_to: z.string().min(1).max(128),
});

export const RuleBranchInSchema = z.object({
  set: z.array(RuleSetItemInSchema).min(1).max(50).nullable().optional(),
  do: z.union([SkipToActionInSchema, EndAndSubmitActionInSchema, EndAndDiscardActionInSchema]).nullable().optional(),
});

export const RuleIfInSchema = z.object({
  match: z.enum(["ALL", "ANY", "NONE"]),
  conditions: z.array(z.discriminatedUnion("family", [ChoiceConditionInSchema, MatchingConditionInSchema, RatingConditionInSchema, FieldConditionInSchema])).min(1).max(50),
});

export const RuleSchemaInSchema = z.object({
  if: RuleIfInSchema,
  then: RuleBranchInSchema,
  else: RuleBranchInSchema.nullable().optional(),
});

export const CreateQuestionNodeRequestSchema = z.object({
  id: z.string().uuid().max(36),
  node_key: z.string().min(1).max(128),
  node_type: z.literal("question"),
  sort_key: z.number().int().gt(0),
  content: z.discriminatedUnion("family", [ChoiceQuestionSchemaInSchema, FieldQuestionSchemaInSchema, MatchingQuestionSchemaInSchema, RatingQuestionSchemaInSchema]),
});

export const CreateRuleNodeRequestSchema = z.object({
  id: z.string().uuid().max(36),
  node_key: z.string().min(1).max(128),
  node_type: z.literal("rule"),
  sort_key: z.number().int().gt(0),
  content: RuleSchemaInSchema,
});
