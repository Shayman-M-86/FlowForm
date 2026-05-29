// This file is auto-generated — do not edit manually

import type { ChoiceAnswerValue, ChoiceOptionMapConfig, FieldAnswerValue, FieldNumericRangesConfig, MatchingAnswerKeyConfig, MatchingAnswerValue, RatingAnswerValue, RatingDirectConfig } from "./subtypes.gen";

export interface BootstrapUserRequest {
  id_token: string;
}

export const BootstrapUserRequestConstraints = {
  id_token: { minLength: 1, maxLength: 8192 },
} as const;

export interface UpdateProfileRequest {
  display_name: string | null;
  nickname: string | null;
  picture: string | null;
}

export const UpdateProfileRequestConstraints = {
  display_name: { minLength: 1, maxLength: 100 },
  nickname: { minLength: 1, maxLength: 100 },
  picture: { minLength: 1, maxLength: 2048 },
} as const;

export interface ChangeEmailRequest {
  email: string;
}

export const ChangeEmailRequestConstraints = {
  email: { minLength: 1, maxLength: 254 },
} as const;

export interface ChangeUsernameRequest {
  username: string;
}

export const ChangeUsernameRequestConstraints = {
  username: { minLength: 1, maxLength: 128, pattern: /^[a-zA-Z0-9_.\-]+$/ },
} as const;

export interface ChoiceRequirementsIn {
  required: string[] | null;
  forbidden: string[] | null;
  any_of: string[] | null;
}

export const ChoiceRequirementsInConstraints = {
  required: { maxItems: 50 },
  forbidden: { maxItems: 50 },
  any_of: { maxItems: 50 },
} as const;

export interface ChoiceConditionIn {
  target_id: string;
  family: "choice";
  requirements: ChoiceRequirementsIn;
}

export const ChoiceConditionInConstraints = {
  target_id: { minLength: 1, maxLength: 128 },
  family: { maxLength: 6 },
} as const;

export interface ChoiceOptionIn {
  id: string;
  label: string;
}

export const ChoiceOptionInConstraints = {
  id: { minLength: 1, maxLength: 128 },
  label: { minLength: 1, maxLength: 1000 },
} as const;

export interface ChoiceDefinitionIn {
  min: number;
  max: number;
  options: ChoiceOptionIn[];
}

export const ChoiceDefinitionInConstraints = {
  min: { minimum: 0 },
  max: { minimum: 1 },
  options: { maxItems: 10 },
} as const;

export interface ChoiceQuestionSchemaIn {
  id: string;
  family: "choice";
  label: string;
  title: string | null;
  definition: ChoiceDefinitionIn;
}

export const ChoiceQuestionSchemaInConstraints = {
  id: { minLength: 1, maxLength: 128 },
  family: { maxLength: 6 },
  label: { minLength: 1, maxLength: 5000 },
  title: { minLength: 1, maxLength: 500 },
} as const;

export interface FieldUIIn {
  placeholder: string;
}

export const FieldUIInConstraints = {
  placeholder: { maxLength: 50 },
} as const;

export interface FieldDefinitionIn {
  field_type: "short_text" | "long_text" | "email" | "number" | "date" | "phone";
  ui?: FieldUIIn;
}

export const FieldDefinitionInConstraints = {
  field_type: { maxLength: 10 },
} as const;

export interface FieldQuestionSchemaIn {
  id: string;
  family: "field";
  label: string;
  title: string | null;
  definition: FieldDefinitionIn;
}

export const FieldQuestionSchemaInConstraints = {
  id: { minLength: 1, maxLength: 128 },
  family: { maxLength: 5 },
  label: { minLength: 1, maxLength: 5000 },
  title: { minLength: 1, maxLength: 500 },
} as const;

export interface MatchingItemIn {
  id: string;
  label: string;
}

export const MatchingItemInConstraints = {
  id: { minLength: 1, maxLength: 128 },
  label: { minLength: 1, maxLength: 250 },
} as const;

export interface MatchingDefinitionIn {
  prompts: MatchingItemIn[];
  matches: MatchingItemIn[];
}

export const MatchingDefinitionInConstraints = {
  prompts: { maxItems: 10 },
  matches: { maxItems: 10 },
} as const;

export interface MatchingQuestionSchemaIn {
  id: string;
  family: "matching";
  label: string;
  title: string | null;
  definition: MatchingDefinitionIn;
}

export const MatchingQuestionSchemaInConstraints = {
  id: { minLength: 1, maxLength: 128 },
  family: { maxLength: 8 },
  label: { minLength: 1, maxLength: 5000 },
  title: { minLength: 1, maxLength: 500 },
} as const;

export interface RatingRangeIn {
  min: number | number;
  max: number | number;
  step: number | number;
}

export interface RatingUIIn {
  left_label: string;
  right_label: string;
}

export const RatingUIInConstraints = {
  left_label: { minLength: 1, maxLength: 50 },
  right_label: { minLength: 1, maxLength: 50 },
} as const;

export interface RatingSliderDefinitionIn {
  variant: "slider";
  range: RatingRangeIn;
  ui: RatingUIIn;
}

export const RatingSliderDefinitionInConstraints = {
  variant: { maxLength: 6 },
} as const;

export interface RatingStarDefinitionIn {
  variant: "stars";
  stars: number;
  ui: RatingUIIn;
}

export const RatingStarDefinitionInConstraints = {
  variant: { maxLength: 5 },
  stars: { minimum: 1, maximum: 12 },
} as const;

export interface RatingEmojiDefinitionIn {
  variant: "emoji";
  emoji_list: "sad_to_happy" | "angry_to_happy" | "disgust_to_happy";
  words: boolean;
  ui: RatingUIIn;
}

export const RatingEmojiDefinitionInConstraints = {
  variant: { maxLength: 5 },
  emoji_list: { maxLength: 16 },
} as const;

export interface RatingQuestionSchemaIn {
  id: string;
  family: "rating";
  label: string;
  title: string | null;
  definition: RatingSliderDefinitionIn | RatingStarDefinitionIn | RatingEmojiDefinitionIn;
}

export const RatingQuestionSchemaInConstraints = {
  id: { minLength: 1, maxLength: 128 },
  family: { maxLength: 6 },
  label: { minLength: 1, maxLength: 5000 },
  title: { minLength: 1, maxLength: 500 },
} as const;

export interface CreateQuestionNodeRequest {
  type: "question";
  sort_key: number;
  content: ChoiceQuestionSchemaIn | FieldQuestionSchemaIn | MatchingQuestionSchemaIn | RatingQuestionSchemaIn;
}

export const CreateQuestionNodeRequestConstraints = {
  type: { maxLength: 8 },
} as const;

export interface MatchingRequirementsIn {
  required: Record<string, unknown>[];
}

export const MatchingRequirementsInConstraints = {
  required: { maxItems: 50 },
} as const;

export interface MatchingConditionIn {
  target_id: string;
  family: "matching";
  requirements: MatchingRequirementsIn;
}

export const MatchingConditionInConstraints = {
  target_id: { minLength: 1, maxLength: 128 },
  family: { maxLength: 8 },
} as const;

export interface RatingRequirementsIn {
  min: number | number | null;
  max: number | number | null;
}

export interface RatingConditionIn {
  target_id: string;
  family: "rating";
  requirements: RatingRequirementsIn;
}

export const RatingConditionInConstraints = {
  target_id: { minLength: 1, maxLength: 128 },
  family: { maxLength: 6 },
} as const;

export interface NumberFieldRequirementsIn {
  type: "number";
  operator: "LT" | "LTE" | "GT" | "GTE" | "EQ" | "NEQ";
  value: number | number;
}

export const NumberFieldRequirementsInConstraints = {
  type: { maxLength: 6 },
  operator: { maxLength: 3 },
} as const;

export interface DateFieldRequirementsIn {
  type: "date";
  operator: "before" | "after";
  value: string;
}

export const DateFieldRequirementsInConstraints = {
  type: { maxLength: 4 },
  operator: { maxLength: 6 },
  value: { maxLength: 10 },
} as const;

export interface FieldConditionIn {
  target_id: string;
  family: "field";
  requirements: NumberFieldRequirementsIn | DateFieldRequirementsIn;
}

export const FieldConditionInConstraints = {
  target_id: { minLength: 1, maxLength: 128 },
  family: { maxLength: 5 },
} as const;

export interface RuleIfIn {
  match: "ALL" | "ANY" | "NONE";
  conditions: (ChoiceConditionIn | MatchingConditionIn | RatingConditionIn | FieldConditionIn)[];
}

export const RuleIfInConstraints = {
  match: { maxLength: 4 },
  conditions: { maxItems: 50 },
} as const;

export interface ThenSetItemIn {
  target_id: string;
  visible: boolean | null;
  required: boolean | null;
}

export const ThenSetItemInConstraints = {
  target_id: { minLength: 1, maxLength: 128 },
} as const;

export interface RuleThenIn {
  set: ThenSetItemIn[];
}

export const RuleThenInConstraints = {
  set: { maxItems: 50 },
} as const;

export interface ElseDoIn {
  skip_to: string | null;
  end_and_submit: boolean | null;
  end_and_discard: boolean | null;
}

export const ElseDoInConstraints = {
  skip_to: { minLength: 1, maxLength: 128 },
} as const;

export interface RuleElseIn {
  do: ElseDoIn;
}

export interface RuleSchemaIn {
  id: string;
  if: RuleIfIn;
  then: RuleThenIn;
  else: RuleElseIn | null;
}

export const RuleSchemaInConstraints = {
  id: { minLength: 1, maxLength: 128 },
} as const;

export interface CreateRuleNodeRequest {
  type: "rule";
  sort_key: number;
  content: RuleSchemaIn;
}

export const CreateRuleNodeRequestConstraints = {
  type: { maxLength: 4 },
} as const;

export type CreateNodeRequest = CreateQuestionNodeRequest | CreateRuleNodeRequest;

export interface UpdateNodeRequest {
  sort_key: number | null;
  content: ChoiceQuestionSchemaIn | FieldQuestionSchemaIn | MatchingQuestionSchemaIn | RatingQuestionSchemaIn | RuleSchemaIn | null;
}

export interface ChoiceOptionMapScoringSchemaIn {
  target: string;
  bucket: string;
  condition: Record<string, unknown> | null;
  strategy: "choice_option_map";
  config: ChoiceOptionMapConfig;
}

export const ChoiceOptionMapScoringSchemaInConstraints = {
  target: { maxLength: 128 },
  bucket: { maxLength: 128 },
  strategy: { maxLength: 17 },
} as const;

export interface NumericRangeScoreIn {
  min: number | number;
  max: number | number;
  score: number | number;
}

export interface FieldNumericRangesScoringSchemaIn {
  target: string;
  bucket: string;
  condition: Record<string, unknown> | null;
  strategy: "field_numeric_ranges";
  config: FieldNumericRangesConfig;
}

export const FieldNumericRangesScoringSchemaInConstraints = {
  target: { maxLength: 128 },
  bucket: { maxLength: 128 },
  strategy: { maxLength: 20 },
} as const;

export interface MatchingPairIn {
  left_id: string;
  right_id: string;
}

export const MatchingPairInConstraints = {
  left_id: { maxLength: 128 },
  right_id: { maxLength: 128 },
} as const;

export interface MatchingAnswerKeyScoringSchemaIn {
  target: string;
  bucket: string;
  condition: Record<string, unknown> | null;
  strategy: "matching_answer_key";
  config: MatchingAnswerKeyConfig;
}

export const MatchingAnswerKeyScoringSchemaInConstraints = {
  target: { maxLength: 128 },
  bucket: { maxLength: 128 },
  strategy: { maxLength: 19 },
} as const;

export interface RatingDirectScoringSchemaIn {
  target: string;
  bucket: string;
  condition: Record<string, unknown> | null;
  strategy: "rating_direct";
  config: RatingDirectConfig;
}

export const RatingDirectScoringSchemaInConstraints = {
  target: { maxLength: 128 },
  bucket: { maxLength: 128 },
  strategy: { maxLength: 13 },
} as const;

export interface CreateScoringRuleRequest {
  scoring_key: string;
  scoring_schema: ChoiceOptionMapScoringSchemaIn | MatchingAnswerKeyScoringSchemaIn | RatingDirectScoringSchemaIn | FieldNumericRangesScoringSchemaIn;
}

export const CreateScoringRuleRequestConstraints = {
  scoring_key: { maxLength: 128 },
} as const;

export interface UpdateScoringRuleRequest {
  scoring_key: string | null;
  scoring_schema: ChoiceOptionMapScoringSchemaIn | MatchingAnswerKeyScoringSchemaIn | RatingDirectScoringSchemaIn | FieldNumericRangesScoringSchemaIn | null;
}

export const UpdateScoringRuleRequestConstraints = {
  scoring_key: { maxLength: 128 },
} as const;

export interface CreateProjectRequest {
  name: string;
  slug: string;
}

export const CreateProjectRequestConstraints = {
  name: { minLength: 1, maxLength: 100 },
  slug: { minLength: 1, maxLength: 80, pattern: /^[a-z0-9]+(?:-[a-z0-9]+)*$/ },
} as const;

export interface UpdateProjectRequest {
  name: string | null;
  slug: string | null;
}

export const UpdateProjectRequestConstraints = {
  name: { minLength: 1, maxLength: 100 },
  slug: { minLength: 1, maxLength: 80, pattern: /^[a-z0-9]+(?:-[a-z0-9]+)*$/ },
} as const;

export interface SendInvitationRequest {
  email: string;
  role_id: number | null;
  invite_message: string | null;
}

export const SendInvitationRequestConstraints = {
  email: { maxLength: 254 },
  role_id: { minimum: 1, maximum: 2147483647 },
  invite_message: { minLength: 1, maxLength: 500 },
} as const;

export interface UpdateMemberRequest {
  role_id: number | null;
  status: "active" | "suspended" | null;
}

export const UpdateMemberRequestConstraints = {
  role_id: { minimum: 1, maximum: 2147483647 },
  status: { maxLength: 9 },
} as const;

export interface CreatePublicLinkRequest {
  name: string;
  assigned_email: string | null;
  requires_auth: boolean;
  expires_at: string | null;
}

export const CreatePublicLinkRequestConstraints = {
  name: { minLength: 1, maxLength: 120 },
  assigned_email: { maxLength: 254 },
  expires_at: { maxLength: 35 },
} as const;

export interface UpdatePublicLinkRequest {
  is_active: boolean | null;
  name: string | null;
  assigned_email: string | null;
  requires_auth: boolean | null;
  expires_at: string | null;
}

export const UpdatePublicLinkRequestConstraints = {
  name: { minLength: 1, maxLength: 120 },
  assigned_email: { maxLength: 254 },
  expires_at: { maxLength: 35 },
} as const;

export interface CreateProjectRoleRequest {
  name: string;
  description: string | null;
  permissions?: ("project:edit" | "project:delete" | "project:manage_members" | "project:manage_roles" | "survey:view" | "survey:create" | "survey:edit" | "survey:delete" | "survey:publish" | "survey:archive" | "submission:view")[];
}

export const CreateProjectRoleRequestConstraints = {
  name: { minLength: 1, maxLength: 80 },
  description: { minLength: 1, maxLength: 500 },
  permissions: { maxItems: 11 },
} as const;

export interface UpdateProjectRoleRequest {
  name: string | null;
  description: string | null;
  permissions: ("project:edit" | "project:delete" | "project:manage_members" | "project:manage_roles" | "survey:view" | "survey:create" | "survey:edit" | "survey:delete" | "survey:publish" | "survey:archive" | "submission:view")[] | null;
}

export const UpdateProjectRoleRequestConstraints = {
  name: { minLength: 1, maxLength: 80 },
  description: { minLength: 1, maxLength: 500 },
  permissions: { maxItems: 11 },
} as const;

export interface AssignSurveyMemberRoleRequest {
  membership_id: number;
  role_id: number;
}

export const AssignSurveyMemberRoleRequestConstraints = {
  membership_id: { minimum: 1, maximum: 2147483647 },
  role_id: { minimum: 1, maximum: 2147483647 },
} as const;

export interface UpdateSurveyMemberRoleRequest {
  role_id: number;
}

export const UpdateSurveyMemberRoleRequestConstraints = {
  role_id: { minimum: 1, maximum: 2147483647 },
} as const;

export interface CreateSurveyRoleRequest {
  name: string;
  description: string | null;
  permissions?: ("survey:view" | "survey:create" | "survey:edit" | "survey:delete" | "survey:publish" | "survey:archive" | "submission:view")[];
}

export const CreateSurveyRoleRequestConstraints = {
  name: { minLength: 1, maxLength: 80 },
  description: { minLength: 1, maxLength: 500 },
  permissions: { maxItems: 7 },
} as const;

export interface UpdateSurveyRoleRequest {
  name: string | null;
  description: string | null;
  permissions: ("survey:view" | "survey:create" | "survey:edit" | "survey:delete" | "survey:publish" | "survey:archive" | "submission:view")[] | null;
}

export const UpdateSurveyRoleRequestConstraints = {
  name: { minLength: 1, maxLength: 80 },
  description: { minLength: 1, maxLength: 500 },
  permissions: { maxItems: 7 },
} as const;

export interface CreateSurveyRequest {
  title: string;
  visibility: "private" | "link_only" | "public";
  public_slug: string | null;
}

export const CreateSurveyRequestConstraints = {
  title: { minLength: 1, maxLength: 200 },
  visibility: { maxLength: 9 },
  public_slug: { minLength: 1, maxLength: 80, pattern: /^[a-z0-9]+(?:-[a-z0-9]+)*$/ },
} as const;

export interface UpdateSurveyRequest {
  title: string | null;
  visibility: "private" | "link_only" | "public" | null;
  public_slug: string | null;
}

export const UpdateSurveyRequestConstraints = {
  title: { minLength: 1, maxLength: 200 },
  visibility: { maxLength: 9 },
  public_slug: { minLength: 1, maxLength: 80, pattern: /^[a-z0-9]+(?:-[a-z0-9]+)*$/ },
} as const;

export interface ChoiceAnswerIn {
  question_key: string;
  answer_family: "choice";
  answer_value: ChoiceAnswerValue;
}

export const ChoiceAnswerInConstraints = {
  question_key: { maxLength: 128 },
  answer_family: { maxLength: 6 },
} as const;

export interface FieldAnswerIn {
  question_key: string;
  answer_family: "field";
  answer_value: FieldAnswerValue;
}

export const FieldAnswerInConstraints = {
  question_key: { maxLength: 128 },
  answer_family: { maxLength: 5 },
} as const;

export interface MatchingAnswerIn {
  question_key: string;
  answer_family: "matching";
  answer_value: MatchingAnswerValue;
}

export const MatchingAnswerInConstraints = {
  question_key: { maxLength: 128 },
  answer_family: { maxLength: 8 },
} as const;

export interface RatingAnswerIn {
  question_key: string;
  answer_family: "rating";
  answer_value: RatingAnswerValue;
}

export const RatingAnswerInConstraints = {
  question_key: { maxLength: 128 },
  answer_family: { maxLength: 6 },
} as const;

export interface SlugSubmissionRequest {
  started_at: string | null;
  submitted_at: string | null;
  answers?: (ChoiceAnswerIn | FieldAnswerIn | MatchingAnswerIn | RatingAnswerIn)[];
  metadata?: Record<string, unknown>;
  public_slug: string;
  survey_version_id: number;
}

export const SlugSubmissionRequestConstraints = {
  started_at: { maxLength: 35 },
  submitted_at: { maxLength: 35 },
  answers: { maxItems: 50 },
  public_slug: { maxLength: 80 },
  survey_version_id: { minimum: 1, maximum: 2147483647 },
} as const;

export interface LinkSubmissionRequest {
  started_at: string | null;
  submitted_at: string | null;
  answers?: (ChoiceAnswerIn | FieldAnswerIn | MatchingAnswerIn | RatingAnswerIn)[];
  metadata?: Record<string, unknown>;
  token: string;
  survey_version_id: number;
}

export const LinkSubmissionRequestConstraints = {
  started_at: { maxLength: 35 },
  submitted_at: { maxLength: 35 },
  answers: { maxItems: 50 },
  token: { maxLength: 256 },
  survey_version_id: { minimum: 1, maximum: 2147483647 },
} as const;
