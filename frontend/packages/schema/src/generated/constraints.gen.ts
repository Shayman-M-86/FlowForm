// This file is auto-generated — do not edit manually

// ──────────────────────────────────────────────────────────────────────────
// Subtypes
// ──────────────────────────────────────────────────────────────────────────

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
  value: { maxLength: 1000 },
} as const;

export const MatchPairConstraints = {
  left_id: { maxLength: 128 },
  right_id: { maxLength: 128 },
} as const;

export const MatchingAnswerValueConstraints = {
  matches: { maxItems: 50 },
} as const;

// ──────────────────────────────────────────────────────────────────────────
// Requests
// ──────────────────────────────────────────────────────────────────────────

export const BootstrapUserRequestConstraints = {
  id_token: { minLength: 1, maxLength: 8192 },
} as const;

export const UpdateProfileRequestConstraints = {
  display_name: { minLength: 1, maxLength: 100 },
  nickname: { minLength: 1, maxLength: 100 },
  picture: { minLength: 1, maxLength: 2048 },
} as const;

export const ChangeEmailRequestConstraints = {
  email: { minLength: 1, maxLength: 254 },
} as const;

export const ChangeUsernameRequestConstraints = {
  username: { minLength: 1, maxLength: 128, pattern: /^[a-zA-Z0-9_.\-]+$/ },
} as const;

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

export const RatingConditionInConstraints = {
  target_id: { minLength: 1, maxLength: 128 },
  family: { maxLength: 6 },
} as const;

export const RatingUIInConstraints = {
  left_label: { minLength: 1, maxLength: 50 },
  right_label: { minLength: 1, maxLength: 50 },
} as const;

export const RatingEmojiDefinitionInConstraints = {
  variant: { maxLength: 5 },
  emoji_list: { maxLength: 16 },
} as const;

export const RatingSliderDefinitionInConstraints = {
  variant: { maxLength: 6 },
} as const;

export const RatingStarDefinitionInConstraints = {
  variant: { maxLength: 5 },
  stars: { minimum: 1, maximum: 12 },
} as const;

export const RatingQuestionSchemaInConstraints = {
  family: { maxLength: 6 },
  label: { minLength: 1, maxLength: 1000 },
  title: { minLength: 0, maxLength: 500 },
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
  node_key: { minLength: 1, maxLength: 128 },
  node_type: { maxLength: 8 },
} as const;

export const CreateRuleNodeRequestConstraints = {
  node_key: { minLength: 1, maxLength: 128 },
  node_type: { maxLength: 4 },
} as const;

export const UpdateNodeRequestConstraints = {
  node_key: { minLength: 1, maxLength: 128 },
  node_type: { maxLength: 8 },
} as const;

export const ChoiceOptionMapScoringSchemaInConstraints = {
  target: { maxLength: 128 },
  bucket: { maxLength: 128 },
  strategy: { maxLength: 17 },
} as const;

export const FieldNumericRangesScoringSchemaInConstraints = {
  target: { maxLength: 128 },
  bucket: { maxLength: 128 },
  strategy: { maxLength: 20 },
} as const;

export const MatchingAnswerKeyScoringSchemaInConstraints = {
  target: { maxLength: 128 },
  bucket: { maxLength: 128 },
  strategy: { maxLength: 19 },
} as const;

export const RatingDirectScoringSchemaInConstraints = {
  target: { maxLength: 128 },
  bucket: { maxLength: 128 },
  strategy: { maxLength: 13 },
} as const;

export const CreateScoringRuleRequestConstraints = {
  scoring_key: { maxLength: 128 },
} as const;

export const UpdateScoringRuleRequestConstraints = {
  scoring_key: { maxLength: 128 },
} as const;

export const CreateProjectRequestConstraints = {
  name: { minLength: 1, maxLength: 100 },
  slug: { minLength: 1, maxLength: 80, pattern: /^[a-z0-9]+(?:-[a-z0-9]+)*$/ },
} as const;

export const UpdateProjectRequestConstraints = {
  name: { minLength: 1, maxLength: 100 },
  slug: { minLength: 1, maxLength: 80, pattern: /^[a-z0-9]+(?:-[a-z0-9]+)*$/ },
} as const;

export const SendInvitationRequestConstraints = {
  email: { maxLength: 254 },
  role_id: { minimum: 1, maximum: 2147483647 },
  invite_message: { minLength: 1, maxLength: 500 },
} as const;

export const UpdateMemberRequestConstraints = {
  role_id: { minimum: 1, maximum: 2147483647 },
  status: { maxLength: 9 },
} as const;

export const CreatePublicLinkRequestConstraints = {
  name: { minLength: 1, maxLength: 120 },
  assigned_email: { maxLength: 254 },
  expires_at: { maxLength: 35 },
} as const;

export const UpdatePublicLinkRequestConstraints = {
  name: { minLength: 1, maxLength: 120 },
  assigned_email: { maxLength: 254 },
  expires_at: { maxLength: 35 },
} as const;

export const CreateProjectRoleRequestConstraints = {
  name: { minLength: 1, maxLength: 80 },
  description: { minLength: 1, maxLength: 500 },
  permissions: { maxItems: 11 },
} as const;

export const UpdateProjectRoleRequestConstraints = {
  name: { minLength: 1, maxLength: 80 },
  description: { minLength: 1, maxLength: 500 },
  permissions: { maxItems: 11 },
} as const;

export const AssignSurveyMemberRoleRequestConstraints = {
  membership_id: { minimum: 1, maximum: 2147483647 },
  role_id: { minimum: 1, maximum: 2147483647 },
} as const;

export const UpdateSurveyMemberRoleRequestConstraints = {
  role_id: { minimum: 1, maximum: 2147483647 },
} as const;

export const CreateSurveyRoleRequestConstraints = {
  name: { minLength: 1, maxLength: 80 },
  description: { minLength: 1, maxLength: 500 },
  permissions: { maxItems: 7 },
} as const;

export const UpdateSurveyRoleRequestConstraints = {
  name: { minLength: 1, maxLength: 80 },
  description: { minLength: 1, maxLength: 500 },
  permissions: { maxItems: 7 },
} as const;

export const CreateSurveyRequestConstraints = {
  title: { minLength: 1, maxLength: 200 },
  visibility: { maxLength: 9 },
  public_slug: { minLength: 1, maxLength: 80, pattern: /^[a-z0-9]+(?:-[a-z0-9]+)*$/ },
} as const;

export const UpdateSurveyRequestConstraints = {
  title: { minLength: 1, maxLength: 200 },
  visibility: { maxLength: 9 },
  public_slug: { minLength: 1, maxLength: 80, pattern: /^[a-z0-9]+(?:-[a-z0-9]+)*$/ },
} as const;

export const ChoiceAnswerInConstraints = {
  question_key: { maxLength: 128 },
  answer_family: { maxLength: 6 },
} as const;

export const FieldAnswerInConstraints = {
  question_key: { maxLength: 128 },
  answer_family: { maxLength: 5 },
} as const;

export const MatchingAnswerInConstraints = {
  question_key: { maxLength: 128 },
  answer_family: { maxLength: 8 },
} as const;

export const RatingAnswerInConstraints = {
  question_key: { maxLength: 128 },
  answer_family: { maxLength: 6 },
} as const;

export const SlugSubmissionRequestConstraints = {
  started_at: { maxLength: 35 },
  submitted_at: { maxLength: 35 },
  answers: { maxItems: 50 },
  public_slug: { maxLength: 80 },
  survey_version_id: { minimum: 1, maximum: 2147483647 },
} as const;

export const LinkSubmissionRequestConstraints = {
  started_at: { maxLength: 35 },
  submitted_at: { maxLength: 35 },
  answers: { maxItems: 50 },
  token: { maxLength: 256 },
  survey_version_id: { minimum: 1, maximum: 2147483647 },
} as const;

// ──────────────────────────────────────────────────────────────────────────
// Responses
// ──────────────────────────────────────────────────────────────────────────

export const CurrentUserResponsesConstraints = {
  auth0_user_id: { maxLength: 255 },
  email: { maxLength: 254 },
  display_name: { maxLength: 100 },
} as const;

export const ProjectResponsesConstraints = {
  name: { maxLength: 100 },
  slug: { maxLength: 80 },
  created_at: { maxLength: 35 },
} as const;

export const CurrentUserProfileResponsesConstraints = {
  auth0_user_id: { maxLength: 255 },
  email: { maxLength: 254 },
  display_name: { maxLength: 100 },
} as const;

export const PasswordChangeTicketResponsesConstraints = {
  ticket_url: { maxLength: 2048 },
} as const;

export const ProjectInvitationResponsesConstraints = {
  invited_email: { maxLength: 254 },
  invite_message: { maxLength: 500 },
  status: { maxLength: 8 },
  expires_at: { maxLength: 35 },
  accepted_at: { maxLength: 35 },
  created_at: { maxLength: 35 },
} as const;

export const MemberUserResponsesConstraints = {
  email: { maxLength: 254 },
  display_name: { maxLength: 100 },
} as const;

export const ProjectMemberResponsesConstraints = {
  status: { maxLength: 9 },
  created_at: { maxLength: 35 },
} as const;

export const NodeResponsesConstraints = {
  node_key: { maxLength: 128 },
  node_type: { maxLength: 8 },
} as const;

export const ScoringRuleResponsesConstraints = {
  scoring_key: { maxLength: 128 },
  created_at: { maxLength: 35 },
  updated_at: { maxLength: 35 },
} as const;

export const PublicLinkResponsesConstraints = {
  name: { maxLength: 120 },
  token_prefix: { maxLength: 32 },
  assigned_email: { maxLength: 254 },
  expires_at: { maxLength: 35 },
  used_at: { maxLength: 35 },
  created_at: { maxLength: 35 },
} as const;

export const CreatePublicLinkResponsesConstraints = {
  token: { maxLength: 256 },
  url: { maxLength: 2048 },
} as const;

export const ProjectRoleResponsesConstraints = {
  name: { maxLength: 120 },
  description: { maxLength: 500 },
  permissions: { maxItems: 11 },
  created_at: { maxLength: 35 },
} as const;

export const SubmitterResponsesConstraints = {
  email: { maxLength: 254 },
  display_name: { maxLength: 100 },
} as const;

export const CoreSubmissionResponsesConstraints = {
  submission_channel: { maxLength: 6 },
  status: { maxLength: 7 },
  started_at: { maxLength: 35 },
  submitted_at: { maxLength: 35 },
  created_at: { maxLength: 35 },
} as const;

export const PaginatedSubmissionsResponsesConstraints = {
  items: { maxItems: 100 },
} as const;

export const AnswerResponsesConstraints = {
  question_key: { maxLength: 128 },
  answer_family: { maxLength: 8 },
  created_at: { maxLength: 35 },
} as const;

export const LinkedSubmissionResponsesConstraints = {
  answers: { maxItems: 50 },
} as const;

export const SurveyRoleResponsesConstraints = {
  name: { maxLength: 120 },
  description: { maxLength: 500 },
  permissions: { maxItems: 7 },
  created_at: { maxLength: 35 },
} as const;

export const SurveyMemberRoleResponsesConstraints = {
  created_at: { maxLength: 35 },
} as const;

export const SurveyResponsesConstraints = {
  title: { maxLength: 200 },
  visibility: { maxLength: 9 },
  public_slug: { maxLength: 80 },
  created_at: { maxLength: 35 },
  updated_at: { maxLength: 35 },
} as const;

export const SurveyVersionResponsesConstraints = {
  status: { maxLength: 9 },
  published_at: { maxLength: 35 },
  created_at: { maxLength: 35 },
  updated_at: { maxLength: 35 },
} as const;

export const PaginatedPublicSurveysResponsesConstraints = {
  items: { maxItems: 100 },
} as const;
