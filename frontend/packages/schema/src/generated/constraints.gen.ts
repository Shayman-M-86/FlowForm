// This file is auto-generated — do not edit manually

// ──────────────────────────────────────────────────────────────────────────
// Subtypes
// ──────────────────────────────────────────────────────────────────────────

export const PublicInvitationResolveResponseConstraints = {
  expires_at: { maxLength: 35 },
  status: { maxLength: 8 },
} as const;

export const AlwaysVisibleConstraints = {
  mode: { maxLength: 6 },
} as const;

export const ChoiceOptionConstraints = {
  id: { minLength: 7, maxLength: 128, pattern: /^option_[A-Za-z0-9_]+$/ },
  label: { minLength: 1, maxLength: 1000 },
} as const;

export const ChoiceResponseConstraints = {
  type: { maxLength: 6 },
} as const;

export const ChoiceSetValidationConstraints = {
  minSelections: { minimum: 0, maximum: 200 },
  maxSelections: { minimum: 1, maximum: 200 },
} as const;

export const ChoiceSetResponseConstraints = {
  type: { maxLength: 10 },
} as const;

export const FieldAnswerConditionConstraints = {
  fieldId: { minLength: 6, maxLength: 128, pattern: /^field_[A-Za-z0-9_]+$/ },
  operator: { maxLength: 12 },
} as const;

export const ConditionalVisibilityConstraints = {
  mode: { maxLength: 11 },
} as const;

export const DateInteractionConstraints = {
  kind: { maxLength: 4 },
  placeholder: { maxLength: 1000 },
} as const;

export const DateValidationConstraints = {
  earliest: { maxLength: 10 },
  latest: { maxLength: 10 },
} as const;

export const DateResponseConstraints = {
  type: { maxLength: 4 },
} as const;

export const DecimalResponseConstraints = {
  type: { maxLength: 7 },
} as const;

export const DividerBlockConstraints = {
  id: { minLength: 6, maxLength: 128, pattern: /^block_[A-Za-z0-9_]+$/ },
  type: { maxLength: 7 },
} as const;

export const HeadingContentConstraints = {
  text: { minLength: 1, maxLength: 1000 },
  level: { minimum: 1, maximum: 6 },
} as const;

export const HeadingBlockConstraints = {
  id: { minLength: 6, maxLength: 128, pattern: /^block_[A-Za-z0-9_]+$/ },
  type: { maxLength: 7 },
} as const;

export const ImageContentConstraints = {
  url: { minLength: 1, maxLength: 2048 },
  altText: { minLength: 1, maxLength: 1000 },
  caption: { maxLength: 1000 },
} as const;

export const ImageBlockConstraints = {
  id: { minLength: 6, maxLength: 128, pattern: /^block_[A-Za-z0-9_]+$/ },
  type: { maxLength: 5 },
} as const;

export const TextInteractionConstraints = {
  kind: { maxLength: 4 },
  presentation: { maxLength: 5 },
  placeholder: { maxLength: 1000 },
} as const;

export const LongTextInteractionConstraints = {
  kind: { maxLength: 9 },
  rows: { minimum: 2, maximum: 20 },
  placeholder: { maxLength: 1000 },
} as const;

export const NumberInteractionConstraints = {
  kind: { maxLength: 6 },
  suffix: { maxLength: 1000 },
  placeholder: { maxLength: 1000 },
} as const;

export const SingleChoiceInteractionConstraints = {
  kind: { maxLength: 13 },
  presentation: { maxLength: 8 },
  options: { minItems: 1, maxItems: 200 },
} as const;

export const MultipleChoiceInteractionConstraints = {
  kind: { maxLength: 15 },
  presentation: { maxLength: 8 },
  options: { minItems: 1, maxItems: 200 },
} as const;

export const RatingInteractionConstraints = {
  kind: { maxLength: 6 },
  presentation: { maxLength: 7 },
  min: { minimum: 0, maximum: 100 },
  max: { minimum: 0, maximum: 100 },
  minLabel: { maxLength: 1000 },
  maxLabel: { maxLength: 1000 },
} as const;

export const SliderInteractionConstraints = {
  kind: { maxLength: 6 },
  minLabel: { maxLength: 1000 },
  maxLabel: { maxLength: 1000 },
} as const;

export const StringValidationConstraints = {
  minLength: { minimum: 0, maximum: 10000 },
  maxLength: { minimum: 0, maximum: 10000 },
  format: { maxLength: 5 },
} as const;

export const StringResponseConstraints = {
  type: { maxLength: 6 },
} as const;

export const IntegerResponseConstraints = {
  type: { maxLength: 7 },
} as const;

export const SurveyFieldConstraints = {
  id: { minLength: 6, maxLength: 128, pattern: /^field_[A-Za-z0-9_]+$/ },
  key: { pattern: /^[a-z0-9_]{1,64}$/ },
  prompt: { minLength: 1, maxLength: 1000 },
  description: { maxLength: 5000 },
  helpText: { maxLength: 1000 },
} as const;

export const InputBlockConstraints = {
  id: { minLength: 6, maxLength: 128, pattern: /^block_[A-Za-z0-9_]+$/ },
  type: { maxLength: 5 },
} as const;

export const NoticeContentConstraints = {
  tone: { maxLength: 11 },
  title: { minLength: 1, maxLength: 1000 },
  text: { minLength: 1, maxLength: 5000 },
} as const;

export const NoticeBlockConstraints = {
  id: { minLength: 6, maxLength: 128, pattern: /^block_[A-Za-z0-9_]+$/ },
  type: { maxLength: 6 },
} as const;

export const ParagraphContentConstraints = {
  text: { minLength: 1, maxLength: 5000 },
} as const;

export const ParagraphBlockConstraints = {
  id: { minLength: 6, maxLength: 128, pattern: /^block_[A-Za-z0-9_]+$/ },
  type: { maxLength: 9 },
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

export const SurveySectionConstraints = {
  id: { minLength: 8, maxLength: 128, pattern: /^section_[A-Za-z0-9_]+$/ },
  title: { minLength: 1, maxLength: 1000 },
  description: { maxLength: 5000 },
  blocks: { minItems: 1, maxItems: 200 },
} as const;

export const SurveyDocumentConstraints = {
  sections: { minItems: 1, maxItems: 100 },
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

export const ResumeSubmissionSessionResponseConstraints = {
  status: { maxLength: 11 },
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
  event_type: { maxLength: 12 },
  field_id: { minLength: 6, maxLength: 128, pattern: /^field_[A-Za-z0-9_]+$/ },
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
