// This file is auto-generated — do not edit manually

import { z } from "zod";

export const zBootstrapUserRequest = z.object({
  id_token: z.string().min(1).max(8192),
});

export const zCurrentUserResponses = z.object({
  id: z.number().int(),
  auth0_user_id: z.string().max(255),
  email: z.string().max(254),
  display_name: z.string().max(100).nullable(),
});

export const zProjectResponses = z.object({
  id: z.number().int(),
  name: z.string().max(100),
  slug: z.string().max(80),
  created_by_user_id: z.number().int().nullable(),
  created_at: z.string().max(35),
});

export const zBootstrapUserResponses = z.object({
  created: z.boolean(),
  user: zCurrentUserResponses,
  default_project: zProjectResponses.nullable().optional(),
});

export const zCurrentUserProfileResponses = z.object({
  id: z.number().int(),
  auth0_user_id: z.string().max(255),
  email: z.string().max(254),
  display_name: z.string().max(100).nullable(),
  email_verified: z.boolean(),
});

export const zUpdateProfileRequest = z.object({
  display_name: z.string().min(1).max(100).nullable().optional(),
  nickname: z.string().min(1).max(100).nullable().optional(),
  picture: z.string().min(1).max(2048).nullable().optional(),
});

export const zChangeEmailRequest = z.object({
  email: z.string().min(1).max(254),
});

export const zChangeUsernameRequest = z.object({
  username: z.string().min(1).max(128).regex(/^[a-zA-Z0-9_.\-]+$/),
});

export const zPasswordChangeTicketResponses = z.object({
  ticket_url: z.string().max(2048),
});

export const zProjectInvitationResponses = z.object({
  id: z.number().int(),
  project_id: z.number().int(),
  project_name: z.string().nullable().optional(),
  invited_email: z.string().max(254),
  invite_message: z.string().max(500).nullable().optional(),
  invited_by_user_id: z.number().int().nullable(),
  invited_by_display: z.string().nullable().optional(),
  role_id: z.number().int().nullable(),
  status: z.union([z.literal("pending"), z.literal("accepted"), z.literal("declined"), z.literal("revoked")]),
  expires_at: z.string().max(35).nullable(),
  accepted_at: z.string().max(35).nullable(),
  created_at: z.string().max(35),
});

export const zMemberUserResponses = z.object({
  id: z.number().int(),
  email: z.string().max(254),
  display_name: z.string().max(100).nullable(),
});

export const zProjectMemberResponses = z.object({
  id: z.number().int(),
  user_id: z.number().int(),
  project_id: z.number().int(),
  role_id: z.number().int().nullable(),
  status: z.union([z.literal("active"), z.literal("suspended")]),
  created_at: z.string().max(35),
  user: zMemberUserResponses,
});

export const zNodeResponses = z.object({
  id: z.number().int(),
  survey_version_id: z.number().int(),
  question_key: z.string().max(128),
  sort_key: z.number().int(),
  node_type: z.union([z.literal("question"), z.literal("rule")]),
  question_schema: z.record(z.string(), z.unknown()),
  created_at: z.string().max(35),
  updated_at: z.string().max(35),
});

export const zChoiceRequirementsIn = z.object({
  required: z.array(z.string().min(1).max(128)).max(50).nullable().optional(),
  forbidden: z.array(z.string().min(1).max(128)).max(50).nullable().optional(),
  any_of: z.array(z.string().min(1).max(128)).max(50).nullable().optional(),
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
  title: z.string().min(1).max(500).nullable().optional(),
  definition: zChoiceDefinitionIn,
});

export const zFieldUIIn = z.object({
  placeholder: z.string().max(50).optional(),
});

export const zFieldDefinitionIn = z.object({
  field_type: z.union([z.literal("short_text"), z.literal("long_text"), z.literal("email"), z.literal("number"), z.literal("date"), z.literal("phone")]),
  ui: zFieldUIIn.optional(),
});

export const zFieldQuestionSchemaIn = z.object({
  id: z.string().min(1).max(128),
  family: z.literal("field"),
  label: z.string().min(1).max(5000),
  title: z.string().min(1).max(500).nullable().optional(),
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
  title: z.string().min(1).max(500).nullable().optional(),
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
  words: z.boolean().optional(),
  ui: zRatingUIIn,
});

export const zRatingQuestionSchemaIn = z.object({
  id: z.string().min(1).max(128),
  family: z.literal("rating"),
  label: z.string().min(1).max(5000),
  title: z.string().min(1).max(500).nullable().optional(),
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
  min: z.union([z.number().int(), z.number()]).nullable().optional(),
  max: z.union([z.number().int(), z.number()]).nullable().optional(),
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
  visible: z.boolean().nullable().optional(),
  required: z.boolean().nullable().optional(),
});

export const zRuleThenIn = z.object({
  set: z.array(zThenSetItemIn).max(50),
});

export const zElseDoIn = z.object({
  skip_to: z.string().min(1).max(128).nullable().optional(),
  end_and_submit: z.boolean().nullable().optional(),
  end_and_discard: z.boolean().nullable().optional(),
});

export const zRuleElseIn = z.object({
  do: zElseDoIn,
});

export const zRuleSchemaIn = z.object({
  id: z.string().min(1).max(128),
  if: zRuleIfIn,
  then: zRuleThenIn,
  else: zRuleElseIn.nullable().optional(),
});

export const zCreateRuleNodeRequest = z.object({
  type: z.literal("rule"),
  sort_key: z.number().int(),
  content: zRuleSchemaIn,
});

export const zCreateNodeRequest = z.discriminatedUnion("type", [zCreateQuestionNodeRequest, zCreateRuleNodeRequest]);

export const zUpdateNodeRequest = z.object({
  sort_key: z.number().int().nullable().optional(),
  content: z.union([z.discriminatedUnion("family", [zChoiceQuestionSchemaIn, zFieldQuestionSchemaIn, zMatchingQuestionSchemaIn, zRatingQuestionSchemaIn]), zRuleSchemaIn]).nullable().optional(),
});

export const zScoringRuleResponses = z.object({
  id: z.number().int(),
  survey_version_id: z.number().int(),
  scoring_key: z.string().max(128),
  scoring_schema: z.record(z.string(), z.unknown()),
  created_at: z.string().max(35),
  updated_at: z.string().max(35),
});

export const zChoiceOptionMapConfig = z.object({
  option_scores: z.record(z.string(), z.unknown()),
  combine: z.union([z.literal("sum"), z.literal("max")]).optional(),
});

export const zChoiceOptionMapScoringSchemaIn = z.object({
  target: z.string().max(128),
  bucket: z.string().max(128),
  condition: z.record(z.string(), z.unknown()).nullable().optional(),
  strategy: z.literal("choice_option_map"),
  config: zChoiceOptionMapConfig,
});

export const zNumericRangeScoreIn = z.object({
  min: z.union([z.number().int(), z.number()]),
  max: z.union([z.number().int(), z.number()]),
  score: z.union([z.number().int(), z.number()]),
});

export const zFieldNumericRangesConfig = z.object({
  ranges: z.array(zNumericRangeScoreIn).max(50),
});

export const zFieldNumericRangesScoringSchemaIn = z.object({
  target: z.string().max(128),
  bucket: z.string().max(128),
  condition: z.record(z.string(), z.unknown()).nullable().optional(),
  strategy: z.literal("field_numeric_ranges"),
  config: zFieldNumericRangesConfig,
});

export const zMatchingPairIn = z.object({
  left_id: z.string().max(128),
  right_id: z.string().max(128),
});

export const zMatchingAnswerKeyConfig = z.object({
  correct_pairs: z.array(zMatchingPairIn).max(50),
  points_per_correct: z.union([z.number().int(), z.number()]).optional(),
  penalty_per_incorrect: z.union([z.number().int(), z.number()]).optional(),
  max_score: z.union([z.number().int(), z.number()]).nullable().optional(),
});

export const zMatchingAnswerKeyScoringSchemaIn = z.object({
  target: z.string().max(128),
  bucket: z.string().max(128),
  condition: z.record(z.string(), z.unknown()).nullable().optional(),
  strategy: z.literal("matching_answer_key"),
  config: zMatchingAnswerKeyConfig,
});

export const zRatingDirectConfig = z.object({
  multiplier: z.union([z.number().int(), z.number()]).optional(),
});

export const zRatingDirectScoringSchemaIn = z.object({
  target: z.string().max(128),
  bucket: z.string().max(128),
  condition: z.record(z.string(), z.unknown()).nullable().optional(),
  strategy: z.literal("rating_direct"),
  config: zRatingDirectConfig,
});

export const zCreateScoringRuleRequest = z.object({
  scoring_key: z.string().max(128),
  scoring_schema: z.discriminatedUnion("strategy", [zChoiceOptionMapScoringSchemaIn, zMatchingAnswerKeyScoringSchemaIn, zRatingDirectScoringSchemaIn, zFieldNumericRangesScoringSchemaIn]),
});

export const zUpdateScoringRuleRequest = z.object({
  scoring_key: z.string().max(128).nullable().optional(),
  scoring_schema: z.discriminatedUnion("strategy", [zChoiceOptionMapScoringSchemaIn, zMatchingAnswerKeyScoringSchemaIn, zRatingDirectScoringSchemaIn, zFieldNumericRangesScoringSchemaIn]).nullable().optional(),
});

export const zCreateProjectRequest = z.object({
  name: z.string().min(1).max(100),
  slug: z.string().min(1).max(80).regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
});

export const zMyProjectPermissionsResponses = z.object({
  permissions: z.array(z.union([z.literal("project:edit"), z.literal("project:delete"), z.literal("project:manage_members"), z.literal("project:manage_roles"), z.literal("survey:view"), z.literal("survey:create"), z.literal("survey:edit"), z.literal("survey:delete"), z.literal("survey:publish"), z.literal("survey:archive"), z.literal("submission:view")])),
});

export const zUpdateProjectRequest = z.object({
  name: z.string().min(1).max(100).nullable().optional(),
  slug: z.string().min(1).max(80).regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/).nullable().optional(),
});

export const zSendInvitationRequest = z.object({
  email: z.string().max(254),
  role_id: z.number().int().gte(1).lte(2147483647).nullable().optional(),
  invite_message: z.string().min(1).max(500).nullable().optional(),
});

export const zUpdateMemberRequest = z.object({
  role_id: z.number().int().gte(1).lte(2147483647).nullable().optional(),
  status: z.union([z.literal("active"), z.literal("suspended")]).nullable().optional(),
});

export const zPublicLinkResponses = z.object({
  id: z.number().int(),
  survey_id: z.number().int(),
  name: z.string().max(120),
  token_prefix: z.string().max(32),
  is_active: z.boolean(),
  requires_auth: z.boolean(),
  assigned_email: z.string().max(254).nullable(),
  expires_at: z.string().max(35).nullable(),
  used_at: z.string().max(35).nullable(),
  created_at: z.string().max(35),
});

export const zListPublicLinksResponses = z.object({
  links: z.array(zPublicLinkResponses),
});

export const zCreatePublicLinkRequest = z.object({
  name: z.string().min(1).max(120),
  assigned_email: z.string().max(254).nullable().optional(),
  requires_auth: z.boolean().optional(),
  expires_at: z.string().max(35).nullable().optional(),
});

export const zCreatePublicLinkResponses = z.object({
  link: zPublicLinkResponses,
  token: z.string().max(256),
  url: z.string().max(2048),
});

export const zUpdatePublicLinkRequest = z.object({
  is_active: z.boolean().nullable().optional(),
  name: z.string().min(1).max(120).nullable().optional(),
  assigned_email: z.string().max(254).nullable().optional(),
  requires_auth: z.boolean().nullable().optional(),
  expires_at: z.string().max(35).nullable().optional(),
});

export const zProjectRoleResponses = z.object({
  id: z.number().int(),
  project_id: z.number().int(),
  name: z.string().max(120),
  description: z.string().max(500).nullable(),
  is_system_role: z.boolean(),
  permissions: z.array(z.union([z.literal("project:edit"), z.literal("project:delete"), z.literal("project:manage_members"), z.literal("project:manage_roles"), z.literal("survey:view"), z.literal("survey:create"), z.literal("survey:edit"), z.literal("survey:delete"), z.literal("survey:publish"), z.literal("survey:archive"), z.literal("submission:view")])).max(11),
  created_at: z.string().max(35),
});

export const zCreateProjectRoleRequest = z.object({
  name: z.string().min(1).max(80),
  description: z.string().min(1).max(500).nullable().optional(),
  permissions: z.array(z.union([z.literal("project:edit"), z.literal("project:delete"), z.literal("project:manage_members"), z.literal("project:manage_roles"), z.literal("survey:view"), z.literal("survey:create"), z.literal("survey:edit"), z.literal("survey:delete"), z.literal("survey:publish"), z.literal("survey:archive"), z.literal("submission:view")])).max(11).optional(),
});

export const zUpdateProjectRoleRequest = z.object({
  name: z.string().min(1).max(80).nullable().optional(),
  description: z.string().min(1).max(500).nullable().optional(),
  permissions: z.array(z.union([z.literal("project:edit"), z.literal("project:delete"), z.literal("project:manage_members"), z.literal("project:manage_roles"), z.literal("survey:view"), z.literal("survey:create"), z.literal("survey:edit"), z.literal("survey:delete"), z.literal("survey:publish"), z.literal("survey:archive"), z.literal("submission:view")])).max(11).nullable().optional(),
});

export const zSubmitterResponses = z.object({
  id: z.number().int(),
  email: z.string().max(254),
  display_name: z.string().max(100).nullable(),
});

export const zCoreSubmissionResponses = z.object({
  id: z.number().int(),
  project_id: z.number().int(),
  survey_id: z.number().int(),
  survey_version_id: z.number().int(),
  response_store_id: z.number().int(),
  submission_channel: z.union([z.literal("link"), z.literal("slug"), z.literal("system")]),
  submitted_by_user_id: z.number().int().nullable(),
  survey_link_id: z.number().int().nullable(),
  submitter: zSubmitterResponses.nullable().optional(),
  is_anonymous: z.boolean(),
  status: z.union([z.literal("pending"), z.literal("stored"), z.literal("failed")]),
  started_at: z.string().max(35).nullable(),
  submitted_at: z.string().max(35).nullable(),
  created_at: z.string().max(35),
});

export const zPaginatedSubmissionsResponses = z.object({
  items: z.array(zCoreSubmissionResponses).max(100),
  total: z.number().int(),
  page: z.number().int(),
  page_size: z.number().int(),
});

export const zAnswerResponses = z.object({
  id: z.number().int(),
  question_key: z.string().max(128),
  answer_family: z.union([z.literal("choice"), z.literal("field"), z.literal("matching"), z.literal("rating")]),
  answer_value: z.record(z.string(), z.unknown()),
  created_at: z.string().max(35),
});

export const zLinkedSubmissionResponses = z.object({
  core: zCoreSubmissionResponses,
  answers: z.array(zAnswerResponses).max(50),
});

export const zSurveyMemberResponses = z.object({
  id: z.number().int(),
  user_id: z.number().int(),
  project_id: z.number().int(),
  role_id: z.number().int().nullable(),
  status: z.string(),
});

export const zSurveyRoleResponses = z.object({
  id: z.number().int(),
  project_id: z.number().int(),
  name: z.string().max(120),
  description: z.string().max(500).nullable(),
  permissions: z.array(z.union([z.literal("survey:view"), z.literal("survey:create"), z.literal("survey:edit"), z.literal("survey:delete"), z.literal("survey:publish"), z.literal("survey:archive"), z.literal("submission:view")])).max(7),
  created_at: z.string().max(35),
});

export const zSurveyMemberRoleResponses = z.object({
  project_id: z.number().int(),
  survey_id: z.number().int(),
  membership_id: z.number().int(),
  role_id: z.number().int(),
  created_at: z.string().max(35),
  member: zSurveyMemberResponses.nullable().optional(),
  role: zSurveyRoleResponses.nullable().optional(),
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
  description: z.string().min(1).max(500).nullable().optional(),
  permissions: z.array(z.union([z.literal("survey:view"), z.literal("survey:create"), z.literal("survey:edit"), z.literal("survey:delete"), z.literal("survey:publish"), z.literal("survey:archive"), z.literal("submission:view")])).max(7).optional(),
});

export const zUpdateSurveyRoleRequest = z.object({
  name: z.string().min(1).max(80).nullable().optional(),
  description: z.string().min(1).max(500).nullable().optional(),
  permissions: z.array(z.union([z.literal("survey:view"), z.literal("survey:create"), z.literal("survey:edit"), z.literal("survey:delete"), z.literal("survey:publish"), z.literal("survey:archive"), z.literal("submission:view")])).max(7).nullable().optional(),
});

export const zSurveyResponses = z.object({
  id: z.number().int(),
  project_id: z.number().int(),
  title: z.string().max(200),
  visibility: z.union([z.literal("private"), z.literal("link_only"), z.literal("public")]),
  public_slug: z.string().max(80).nullable(),
  default_response_store_id: z.number().int().nullable(),
  published_version_id: z.number().int().nullable(),
  created_by_user_id: z.number().int().nullable(),
  created_at: z.string().max(35),
  updated_at: z.string().max(35),
});

export const zCreateSurveyRequest = z.object({
  title: z.string().min(1).max(200),
  visibility: z.union([z.literal("private"), z.literal("link_only"), z.literal("public")]).optional(),
  public_slug: z.string().min(1).max(80).regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/).nullable().optional(),
});

export const zUpdateSurveyRequest = z.object({
  title: z.string().min(1).max(200).nullable().optional(),
  visibility: z.union([z.literal("private"), z.literal("link_only"), z.literal("public")]).nullable().optional(),
  public_slug: z.string().min(1).max(80).regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/).nullable().optional(),
});

export const zSurveyVersionResponses = z.object({
  id: z.number().int(),
  survey_id: z.number().int(),
  version_number: z.number().int(),
  status: z.union([z.literal("draft"), z.literal("published"), z.literal("archived")]),
  compiled_schema: z.record(z.string(), z.unknown()).nullable(),
  published_at: z.string().max(35).nullable(),
  created_by_user_id: z.number().int().nullable(),
  created_at: z.string().max(35),
  updated_at: z.string().max(35),
});

export const zPaginatedPublicSurveysResponses = z.object({
  items: z.array(zSurveyResponses).max(100),
  total: z.number().int(),
  page: z.number().int(),
  page_size: z.number().int(),
});

export const zPublicSurveyResponses = z.object({
  survey: zSurveyResponses,
  published_version: zSurveyVersionResponses.nullable().optional(),
});

export const zResolveLinkResponses = z.object({
  link: zPublicLinkResponses,
  survey: zSurveyResponses.nullable().optional(),
  published_version: zSurveyVersionResponses.nullable().optional(),
});

export const zChoiceAnswerValue = z.object({
  selected: z.array(z.string().max(128)).max(50),
});

export const zChoiceAnswerIn = z.object({
  question_key: z.string().max(128),
  answer_family: z.literal("choice"),
  answer_value: zChoiceAnswerValue,
});

export const zFieldAnswerValue = z.object({
  value: z.union([z.string().max(5000), z.number().int(), z.number(), z.boolean(), z.string().max(10)]).nullable(),
});

export const zFieldAnswerIn = z.object({
  question_key: z.string().max(128),
  answer_family: z.literal("field"),
  answer_value: zFieldAnswerValue,
});

export const zMatchPair = z.object({
  left_id: z.string().max(128),
  right_id: z.string().max(128),
});

export const zMatchingAnswerValue = z.object({
  matches: z.array(zMatchPair).max(50),
});

export const zMatchingAnswerIn = z.object({
  question_key: z.string().max(128),
  answer_family: z.literal("matching"),
  answer_value: zMatchingAnswerValue,
});

export const zRatingAnswerValue = z.object({
  value: z.union([z.number().int(), z.number()]),
});

export const zRatingAnswerIn = z.object({
  question_key: z.string().max(128),
  answer_family: z.literal("rating"),
  answer_value: zRatingAnswerValue,
});

export const zSlugSubmissionRequest = z.object({
  started_at: z.string().max(35).nullable().optional(),
  submitted_at: z.string().max(35).nullable().optional(),
  answers: z.array(z.discriminatedUnion("answer_family", [zChoiceAnswerIn, zFieldAnswerIn, zMatchingAnswerIn, zRatingAnswerIn])).max(50).optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  public_slug: z.string().max(80),
  survey_version_id: z.number().int().gte(1).lte(2147483647),
});

export const zLinkSubmissionRequest = z.object({
  started_at: z.string().max(35).nullable().optional(),
  submitted_at: z.string().max(35).nullable().optional(),
  answers: z.array(z.discriminatedUnion("answer_family", [zChoiceAnswerIn, zFieldAnswerIn, zMatchingAnswerIn, zRatingAnswerIn])).max(50).optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  token: z.string().max(256),
  survey_version_id: z.number().int().gte(1).lte(2147483647),
});
