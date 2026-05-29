// This file is auto-generated — do not edit manually

import { z } from "zod";

import { zChoiceAnswerValue, zChoiceOptionMapConfig, zFieldAnswerValue, zFieldNumericRangesConfig, zMatchingAnswerKeyConfig, zMatchingAnswerValue, zRatingAnswerValue, zRatingDirectConfig } from "./subtypes.zod.gen";

export const zBootstrapUserRequest = z.object({
  id_token: z.string().min(1).max(8192),
});

export const zUpdateProfileRequest = z.object({
  display_name: z.string().min(1).max(100).nullable(),
  nickname: z.string().min(1).max(100).nullable(),
  picture: z.string().min(1).max(2048).nullable(),
});

export const zChangeEmailRequest = z.object({
  email: z.string().min(1).max(254),
});

export const zChangeUsernameRequest = z.object({
  username: z.string().min(1).max(128).regex(/^[a-zA-Z0-9_.\-]+$/),
});

export const zChoiceRequirementsIn = z.object({
  required: z.array(z.string().min(1).max(128)).max(50).nullable(),
  forbidden: z.array(z.string().min(1).max(128)).max(50).nullable(),
  any_of: z.array(z.string().min(1).max(128)).max(50).nullable(),
});

export const zChoiceConditionIn = z.object({
  target_id: z.string().min(1).max(128),
  family: z.literal("choice"),
  requirements: zChoiceRequirementsIn,
});

export const zChoiceOptionIn = z.object({
  id: z.string().min(1).max(128),
  label: z.string().min(1).max(1000),
});

export const zChoiceDefinitionIn = z.object({
  min: z.number().int().gte(0),
  max: z.number().int().gte(1),
  options: z.array(zChoiceOptionIn).max(10),
});

export const zChoiceQuestionSchemaIn = z.object({
  id: z.string().min(1).max(128),
  family: z.literal("choice"),
  label: z.string().min(1).max(5000),
  title: z.string().min(1).max(500).nullable(),
  definition: zChoiceDefinitionIn,
});

export const zFieldUIIn = z.object({
  placeholder: z.string().max(50),
});

export const zFieldDefinitionIn = z.object({
  field_type: z.union([z.literal("short_text"), z.literal("long_text"), z.literal("email"), z.literal("number"), z.literal("date"), z.literal("phone")]),
  ui: zFieldUIIn.optional(),
});

export const zFieldQuestionSchemaIn = z.object({
  id: z.string().min(1).max(128),
  family: z.literal("field"),
  label: z.string().min(1).max(5000),
  title: z.string().min(1).max(500).nullable(),
  definition: zFieldDefinitionIn,
});

export const zMatchingItemIn = z.object({
  id: z.string().min(1).max(128),
  label: z.string().min(1).max(250),
});

export const zMatchingDefinitionIn = z.object({
  prompts: z.array(zMatchingItemIn).max(10),
  matches: z.array(zMatchingItemIn).max(10),
});

export const zMatchingQuestionSchemaIn = z.object({
  id: z.string().min(1).max(128),
  family: z.literal("matching"),
  label: z.string().min(1).max(5000),
  title: z.string().min(1).max(500).nullable(),
  definition: zMatchingDefinitionIn,
});

export const zRatingRangeIn = z.object({
  min: z.union([z.number().int(), z.number()]),
  max: z.union([z.number().int(), z.number()]),
  step: z.union([z.number().int(), z.number()]),
});

export const zRatingUIIn = z.object({
  left_label: z.string().min(1).max(50),
  right_label: z.string().min(1).max(50),
});

export const zRatingSliderDefinitionIn = z.object({
  variant: z.literal("slider"),
  range: zRatingRangeIn,
  ui: zRatingUIIn,
});

export const zRatingStarDefinitionIn = z.object({
  variant: z.literal("stars"),
  stars: z.number().int().gte(1).lte(12),
  ui: zRatingUIIn,
});

export const zRatingEmojiDefinitionIn = z.object({
  variant: z.literal("emoji"),
  emoji_list: z.union([z.literal("sad_to_happy"), z.literal("angry_to_happy"), z.literal("disgust_to_happy")]),
  words: z.boolean(),
  ui: zRatingUIIn,
});

export const zRatingQuestionSchemaIn = z.object({
  id: z.string().min(1).max(128),
  family: z.literal("rating"),
  label: z.string().min(1).max(5000),
  title: z.string().min(1).max(500).nullable(),
  definition: z.discriminatedUnion("variant", [zRatingSliderDefinitionIn, zRatingStarDefinitionIn, zRatingEmojiDefinitionIn]),
});

export const zCreateQuestionNodeRequest = z.object({
  type: z.literal("question"),
  sort_key: z.number().int(),
  content: z.discriminatedUnion("family", [zChoiceQuestionSchemaIn, zFieldQuestionSchemaIn, zMatchingQuestionSchemaIn, zRatingQuestionSchemaIn]),
});

export const zMatchingRequirementsIn = z.object({
  required: z.array(z.record(z.string(), z.unknown())).max(50),
});

export const zMatchingConditionIn = z.object({
  target_id: z.string().min(1).max(128),
  family: z.literal("matching"),
  requirements: zMatchingRequirementsIn,
});

export const zRatingRequirementsIn = z.object({
  min: z.union([z.number().int(), z.number()]).nullable(),
  max: z.union([z.number().int(), z.number()]).nullable(),
});

export const zRatingConditionIn = z.object({
  target_id: z.string().min(1).max(128),
  family: z.literal("rating"),
  requirements: zRatingRequirementsIn,
});

export const zNumberFieldRequirementsIn = z.object({
  type: z.literal("number"),
  operator: z.union([z.literal("LT"), z.literal("LTE"), z.literal("GT"), z.literal("GTE"), z.literal("EQ"), z.literal("NEQ")]),
  value: z.union([z.number().int(), z.number()]),
});

export const zDateFieldRequirementsIn = z.object({
  type: z.literal("date"),
  operator: z.union([z.literal("before"), z.literal("after")]),
  value: z.string().max(10),
});

export const zFieldConditionIn = z.object({
  target_id: z.string().min(1).max(128),
  family: z.literal("field"),
  requirements: z.union([zNumberFieldRequirementsIn, zDateFieldRequirementsIn]),
});

export const zRuleIfIn = z.object({
  match: z.union([z.literal("ALL"), z.literal("ANY"), z.literal("NONE")]),
  conditions: z.array(z.discriminatedUnion("family", [zChoiceConditionIn, zMatchingConditionIn, zRatingConditionIn, zFieldConditionIn])).max(50),
});

export const zThenSetItemIn = z.object({
  target_id: z.string().min(1).max(128),
  visible: z.boolean().nullable(),
  required: z.boolean().nullable(),
});

export const zRuleThenIn = z.object({
  set: z.array(zThenSetItemIn).max(50),
});

export const zElseDoIn = z.object({
  skip_to: z.string().min(1).max(128).nullable(),
  end_and_submit: z.boolean().nullable(),
  end_and_discard: z.boolean().nullable(),
});

export const zRuleElseIn = z.object({
  do: zElseDoIn,
});

export const zRuleSchemaIn = z.object({
  id: z.string().min(1).max(128),
  if: zRuleIfIn,
  then: zRuleThenIn,
  else: zRuleElseIn.nullable(),
});

export const zCreateRuleNodeRequest = z.object({
  type: z.literal("rule"),
  sort_key: z.number().int(),
  content: zRuleSchemaIn,
});

export const zCreateNodeRequest = z.discriminatedUnion("type", [zCreateQuestionNodeRequest, zCreateRuleNodeRequest]);

export const zUpdateNodeRequest = z.object({
  sort_key: z.number().int().nullable(),
  content: z.union([z.discriminatedUnion("family", [zChoiceQuestionSchemaIn, zFieldQuestionSchemaIn, zMatchingQuestionSchemaIn, zRatingQuestionSchemaIn]), zRuleSchemaIn]).nullable(),
});

export const zChoiceOptionMapScoringSchemaIn = z.object({
  target: z.string().max(128),
  bucket: z.string().max(128),
  condition: z.record(z.string(), z.unknown()).nullable(),
  strategy: z.literal("choice_option_map"),
  config: zChoiceOptionMapConfig,
});

export const zNumericRangeScoreIn = z.object({
  min: z.union([z.number().int(), z.number()]),
  max: z.union([z.number().int(), z.number()]),
  score: z.union([z.number().int(), z.number()]),
});

export const zFieldNumericRangesScoringSchemaIn = z.object({
  target: z.string().max(128),
  bucket: z.string().max(128),
  condition: z.record(z.string(), z.unknown()).nullable(),
  strategy: z.literal("field_numeric_ranges"),
  config: zFieldNumericRangesConfig,
});

export const zMatchingPairIn = z.object({
  left_id: z.string().max(128),
  right_id: z.string().max(128),
});

export const zMatchingAnswerKeyScoringSchemaIn = z.object({
  target: z.string().max(128),
  bucket: z.string().max(128),
  condition: z.record(z.string(), z.unknown()).nullable(),
  strategy: z.literal("matching_answer_key"),
  config: zMatchingAnswerKeyConfig,
});

export const zRatingDirectScoringSchemaIn = z.object({
  target: z.string().max(128),
  bucket: z.string().max(128),
  condition: z.record(z.string(), z.unknown()).nullable(),
  strategy: z.literal("rating_direct"),
  config: zRatingDirectConfig,
});

export const zCreateScoringRuleRequest = z.object({
  scoring_key: z.string().max(128),
  scoring_schema: z.discriminatedUnion("strategy", [zChoiceOptionMapScoringSchemaIn, zMatchingAnswerKeyScoringSchemaIn, zRatingDirectScoringSchemaIn, zFieldNumericRangesScoringSchemaIn]),
});

export const zUpdateScoringRuleRequest = z.object({
  scoring_key: z.string().max(128).nullable(),
  scoring_schema: z.discriminatedUnion("strategy", [zChoiceOptionMapScoringSchemaIn, zMatchingAnswerKeyScoringSchemaIn, zRatingDirectScoringSchemaIn, zFieldNumericRangesScoringSchemaIn]).nullable(),
});

export const zCreateProjectRequest = z.object({
  name: z.string().min(1).max(100),
  slug: z.string().min(1).max(80).regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
});

export const zUpdateProjectRequest = z.object({
  name: z.string().min(1).max(100).nullable(),
  slug: z.string().min(1).max(80).regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/).nullable(),
});

export const zSendInvitationRequest = z.object({
  email: z.string().max(254),
  role_id: z.number().int().gte(1).lte(2147483647).nullable(),
  invite_message: z.string().min(1).max(500).nullable(),
});

export const zUpdateMemberRequest = z.object({
  role_id: z.number().int().gte(1).lte(2147483647).nullable(),
  status: z.union([z.literal("active"), z.literal("suspended")]).nullable(),
});

export const zCreatePublicLinkRequest = z.object({
  name: z.string().min(1).max(120),
  assigned_email: z.string().max(254).nullable(),
  requires_auth: z.boolean(),
  expires_at: z.string().max(35).nullable(),
});

export const zUpdatePublicLinkRequest = z.object({
  is_active: z.boolean().nullable(),
  name: z.string().min(1).max(120).nullable(),
  assigned_email: z.string().max(254).nullable(),
  requires_auth: z.boolean().nullable(),
  expires_at: z.string().max(35).nullable(),
});

export const zCreateProjectRoleRequest = z.object({
  name: z.string().min(1).max(80),
  description: z.string().min(1).max(500).nullable(),
  permissions: z.array(z.union([z.literal("project:edit"), z.literal("project:delete"), z.literal("project:manage_members"), z.literal("project:manage_roles"), z.literal("survey:view"), z.literal("survey:create"), z.literal("survey:edit"), z.literal("survey:delete"), z.literal("survey:publish"), z.literal("survey:archive"), z.literal("submission:view")])).max(11).optional(),
});

export const zUpdateProjectRoleRequest = z.object({
  name: z.string().min(1).max(80).nullable(),
  description: z.string().min(1).max(500).nullable(),
  permissions: z.array(z.union([z.literal("project:edit"), z.literal("project:delete"), z.literal("project:manage_members"), z.literal("project:manage_roles"), z.literal("survey:view"), z.literal("survey:create"), z.literal("survey:edit"), z.literal("survey:delete"), z.literal("survey:publish"), z.literal("survey:archive"), z.literal("submission:view")])).max(11).nullable(),
});

export const zAssignSurveyMemberRoleRequest = z.object({
  membership_id: z.number().int().gte(1).lte(2147483647),
  role_id: z.number().int().gte(1).lte(2147483647),
});

export const zUpdateSurveyMemberRoleRequest = z.object({
  role_id: z.number().int().gte(1).lte(2147483647),
});

export const zCreateSurveyRoleRequest = z.object({
  name: z.string().min(1).max(80),
  description: z.string().min(1).max(500).nullable(),
  permissions: z.array(z.union([z.literal("survey:view"), z.literal("survey:create"), z.literal("survey:edit"), z.literal("survey:delete"), z.literal("survey:publish"), z.literal("survey:archive"), z.literal("submission:view")])).max(7).optional(),
});

export const zUpdateSurveyRoleRequest = z.object({
  name: z.string().min(1).max(80).nullable(),
  description: z.string().min(1).max(500).nullable(),
  permissions: z.array(z.union([z.literal("survey:view"), z.literal("survey:create"), z.literal("survey:edit"), z.literal("survey:delete"), z.literal("survey:publish"), z.literal("survey:archive"), z.literal("submission:view")])).max(7).nullable(),
});

export const zCreateSurveyRequest = z.object({
  title: z.string().min(1).max(200),
  visibility: z.union([z.literal("private"), z.literal("link_only"), z.literal("public")]),
  public_slug: z.string().min(1).max(80).regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/).nullable(),
});

export const zUpdateSurveyRequest = z.object({
  title: z.string().min(1).max(200).nullable(),
  visibility: z.union([z.literal("private"), z.literal("link_only"), z.literal("public")]).nullable(),
  public_slug: z.string().min(1).max(80).regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/).nullable(),
});

export const zChoiceAnswerIn = z.object({
  question_key: z.string().max(128),
  answer_family: z.literal("choice"),
  answer_value: zChoiceAnswerValue,
});

export const zFieldAnswerIn = z.object({
  question_key: z.string().max(128),
  answer_family: z.literal("field"),
  answer_value: zFieldAnswerValue,
});

export const zMatchingAnswerIn = z.object({
  question_key: z.string().max(128),
  answer_family: z.literal("matching"),
  answer_value: zMatchingAnswerValue,
});

export const zRatingAnswerIn = z.object({
  question_key: z.string().max(128),
  answer_family: z.literal("rating"),
  answer_value: zRatingAnswerValue,
});

export const zSlugSubmissionRequest = z.object({
  started_at: z.string().max(35).nullable(),
  submitted_at: z.string().max(35).nullable(),
  answers: z.array(z.discriminatedUnion("answer_family", [zChoiceAnswerIn, zFieldAnswerIn, zMatchingAnswerIn, zRatingAnswerIn])).max(50).optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  public_slug: z.string().max(80),
  survey_version_id: z.number().int().gte(1).lte(2147483647),
});

export const zLinkSubmissionRequest = z.object({
  started_at: z.string().max(35).nullable(),
  submitted_at: z.string().max(35).nullable(),
  answers: z.array(z.discriminatedUnion("answer_family", [zChoiceAnswerIn, zFieldAnswerIn, zMatchingAnswerIn, zRatingAnswerIn])).max(50).optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  token: z.string().max(256),
  survey_version_id: z.number().int().gte(1).lte(2147483647),
});
