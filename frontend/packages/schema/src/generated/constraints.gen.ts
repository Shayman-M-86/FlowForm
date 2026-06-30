// This file is auto-generated — do not edit manually

// ──────────────────────────────────────────────────────────────────────────
// Subtypes
// ──────────────────────────────────────────────────────────────────────────

export const PublicInvitationResolveResponseConstraints = {
  expires_at: { maxLength: 35 },
  status: { maxLength: 8 },
} as const;

export const SurveyAccessLinkResponseConstraints = {
  id: { maxLength: 36 },
  name: { maxLength: 120 },
  token: { maxLength: 256 },
  link_type: { maxLength: 13 },
  assignment_source: { maxLength: 9 },
  assigned_participant_id: { maxLength: 36 },
  expires_at: { maxLength: 35 },
  used_at: { maxLength: 35 },
  emailed_at: { maxLength: 35 },
  created_at: { maxLength: 35 },
} as const;

export const LinkTokenAccessConstraints = {
  type: { maxLength: 10 },
  token: { maxLength: 256 },
} as const;

export const PublicSlugAccessConstraints = {
  type: { maxLength: 11 },
  public_slug: { maxLength: 80 },
} as const;

export const StartSubmissionSessionResponseConstraints = {
  status: { maxLength: 11 },
  started_at: { maxLength: 35 },
  expires_at: { maxLength: 35 },
} as const;

export const ChoiceAnswerValueConstraints = {
  selected: { minItems: 1, maxItems: 10 },
} as const;

export const DateFieldAnswerValueConstraints = {
  field_type: { maxLength: 4 },
  date: { maxLength: 10 },
} as const;

export const EmailFieldAnswerValueConstraints = {
  field_type: { maxLength: 5 },
  email: { maxLength: 254 },
} as const;

export const EmojiRatingAnswerValueConstraints = {
  variant: { maxLength: 5 },
  number: { minimum: 1, maximum: 12 },
} as const;

export const LongTextFieldAnswerValueConstraints = {
  field_type: { maxLength: 9 },
  text: { minLength: 1, maxLength: 1000 },
} as const;

export const MatchingAnswerPairConstraints = {
  prompt_id: { minLength: 1, maxLength: 128 },
  match_id: { minLength: 1, maxLength: 128 },
} as const;

export const MatchingAnswerValueConstraints = {
  pairs: { minItems: 1, maxItems: 10 },
} as const;

export const NumberFieldAnswerValueConstraints = {
  field_type: { maxLength: 6 },
  number: { minimum: -1000000, maximum: 1000000 },
} as const;

export const PhoneFieldAnswerValueConstraints = {
  field_type: { maxLength: 5 },
  phone: { minLength: 1, maxLength: 64 },
} as const;

export const ShortTextFieldAnswerValueConstraints = {
  field_type: { maxLength: 10 },
  text: { minLength: 1, maxLength: 1000 },
} as const;

export const SliderRatingAnswerValueConstraints = {
  variant: { maxLength: 6 },
  number: { minimum: -1000, maximum: 1000 },
} as const;

export const StarsRatingAnswerValueConstraints = {
  variant: { maxLength: 5 },
  number: { minimum: 1, maximum: 12 },
} as const;

export const SubmissionSessionAnswerResponseConstraints = {
  question_node_id: { maxLength: 36 },
  node_key: { maxLength: 128 },
  state: { maxLength: 8 },
  answer_family: { maxLength: 8 },
  client_mutation_id: { maxLength: 36 },
  saved_at: { maxLength: 35 },
} as const;

export const CompleteSubmissionSessionResponseConstraints = {
  status: { maxLength: 9 },
  completed_at: { maxLength: 35 },
} as const;

export const SubjectResponseConstraints = {
  id: { maxLength: 36 },
  canonical_subject_id: { maxLength: 36 },
  participant_id: { maxLength: 36 },
  created_at: { maxLength: 35 },
} as const;

export const SubjectIdentityResponseConstraints = {
  id: { maxLength: 36 },
  attached_at: { maxLength: 35 },
  revoked_at: { maxLength: 35 },
} as const;

export const SubjectDetailResponseConstraints = {
  id: { maxLength: 36 },
  canonical_subject_id: { maxLength: 36 },
  participant_id: { maxLength: 36 },
  created_at: { maxLength: 35 },
} as const;

export const CreateSurveyAccessLinkResponseConstraints = {
  url: { maxLength: 2048 },
} as const;

export const QuestionNodeResponseConstraints = {
  id: { maxLength: 36 },
  node_key: { maxLength: 128 },
  node_type: { maxLength: 8 },
} as const;

export const RuleNodeResponseConstraints = {
  id: { maxLength: 36 },
  node_key: { maxLength: 128 },
  node_type: { maxLength: 4 },
} as const;

export const ChoiceOptionMapConfigConstraints = {
  combine: { maxLength: 3 },
} as const;

export const FieldNumericRangesConfigConstraints = {
  ranges: { maxItems: 50 },
} as const;

export const MatchingAnswerKeyConfigConstraints = {
  correct_pairs: { maxItems: 50 },
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

export const ResolveSurveyAccessLinkTokenRequestConstraints = {
  token: { minLength: 1, maxLength: 256 },
} as const;

export const SaveSubmissionSessionAnswerRequestConstraints = {
  client_mutation_id: { maxLength: 36 },
  state: { maxLength: 8 },
  answer_family: { maxLength: 8 },
} as const;

export const SubmissionSessionEventRequestConstraints = {
  event_type: { maxLength: 15 },
  question_node_id: { maxLength: 36 },
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

export const CreateParticipantRequestConstraints = {
  email: { maxLength: 254 },
  subject_code: { minLength: 1, maxLength: 128 },
} as const;

export const UpdateParticipantRequestConstraints = {
  email: { maxLength: 254 },
  subject_code: { minLength: 1, maxLength: 128 },
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

export const CreateProjectRequestConstraints = {
  name: { minLength: 1, maxLength: 100 },
  slug: { minLength: 1, maxLength: 80, pattern: /^[a-z0-9]+(?:-[a-z0-9]+)*$/ },
} as const;

export const UpdateProjectRequestConstraints = {
  name: { minLength: 1, maxLength: 100 },
  slug: { minLength: 1, maxLength: 80, pattern: /^[a-z0-9]+(?:-[a-z0-9]+)*$/ },
} as const;

export const UpdateSubjectRequestConstraints = {
  subject_code: { minLength: 1, maxLength: 128 },
} as const;

export const CreateSurveyAccessLinkRequestConstraints = {
  name: { minLength: 1, maxLength: 120 },
  link_type: { maxLength: 13 },
  assignment_source: { maxLength: 9 },
  assigned_participant_id: { maxLength: 36 },
  expires_at: { maxLength: 35 },
} as const;

export const UpdateSurveyAccessLinkRequestConstraints = {
  name: { minLength: 1, maxLength: 120 },
  link_type: { maxLength: 13 },
  assignment_source: { maxLength: 9 },
  assigned_participant_id: { maxLength: 36 },
  expires_at: { maxLength: 35 },
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

export const RatingRangeInConstraints = {
  min: { minimum: -1000, maximum: 1000 },
  max: { minimum: -1000, maximum: 1000 },
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

export const UpdateNodeRequestConstraints = {
  id: { maxLength: 36 },
  node_key: { minLength: 1, maxLength: 128 },
  node_type: { maxLength: 8 },
} as const;

export const AssignSurveyMemberRoleRequestConstraints = {
  membership_id: { minimum: 1, maximum: 2147483647 },
  role_id: { minimum: 1, maximum: 2147483647 },
} as const;

export const UpdateSurveyMemberRoleRequestConstraints = {
  role_id: { minimum: 1, maximum: 2147483647 },
} as const;

export const ExportSurveyResponsesRequestConstraints = {
  format: { maxLength: 4 },
  session_ids: { maxItems: 100 },
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

export const CurrentUserProfileResponsesConstraints = {
  auth0_user_id: { maxLength: 255 },
  email: { maxLength: 254 },
  display_name: { maxLength: 100 },
} as const;

export const PasswordChangeTicketResponsesConstraints = {
  ticket_url: { maxLength: 2048 },
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

export const ParticipantResponsesConstraints = {
  id: { maxLength: 36 },
  subject_id: { maxLength: 36 },
  email: { maxLength: 254 },
  created_at: { maxLength: 35 },
} as const;

export const ProjectRoleResponsesConstraints = {
  name: { maxLength: 120 },
  description: { maxLength: 500 },
  permissions: { maxItems: 11 },
  created_at: { maxLength: 35 },
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

export const SurveyResponseSummaryResponsesConstraints = {
  session_id: { maxLength: 36 },
  status: { maxLength: 11 },
  started_at: { maxLength: 35 },
  completed_at: { maxLength: 35 },
  last_activity_at: { maxLength: 35 },
} as const;

export const PaginatedSurveyResponsesResponsesConstraints = {
  items: { maxItems: 100 },
} as const;

export const SurveyResponseAnswerResponsesConstraints = {
  question_node_id: { maxLength: 36 },
  state: { maxLength: 8 },
  answer_family: { maxLength: 8 },
} as const;

export const SurveyResponseDetailResponsesConstraints = {
  answers: { maxItems: 50 },
} as const;

export const SurveyResponseHistoryResponsesConstraints = {
  revisions: { maxItems: 50 },
} as const;

export const ScoringRuleResponsesConstraints = {
  scoring_key: { maxLength: 128 },
  created_at: { maxLength: 35 },
  updated_at: { maxLength: 35 },
} as const;
