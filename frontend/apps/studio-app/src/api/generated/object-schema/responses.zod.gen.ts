// This file is auto-generated — do not edit manually

import { z } from "zod";

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
  default_project: zProjectResponses.nullable(),
});

export const zCurrentUserProfileResponses = z.object({
  id: z.number().int(),
  auth0_user_id: z.string().max(255),
  email: z.string().max(254),
  display_name: z.string().max(100).nullable(),
  email_verified: z.boolean(),
});

export const zPasswordChangeTicketResponses = z.object({
  ticket_url: z.string().max(2048),
});

export const zProjectInvitationResponses = z.object({
  id: z.number().int(),
  project_id: z.number().int(),
  project_name: z.string().nullable(),
  invited_email: z.string().max(254),
  invite_message: z.string().max(500).nullable(),
  invited_by_user_id: z.number().int().nullable(),
  invited_by_display: z.string().nullable(),
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

export const zScoringRuleResponses = z.object({
  id: z.number().int(),
  survey_version_id: z.number().int(),
  scoring_key: z.string().max(128),
  scoring_schema: z.record(z.string(), z.unknown()),
  created_at: z.string().max(35),
  updated_at: z.string().max(35),
});

export const zMyProjectPermissionsResponses = z.object({
  permissions: z.array(z.union([z.literal("project:edit"), z.literal("project:delete"), z.literal("project:manage_members"), z.literal("project:manage_roles"), z.literal("survey:view"), z.literal("survey:create"), z.literal("survey:edit"), z.literal("survey:delete"), z.literal("survey:publish"), z.literal("survey:archive"), z.literal("submission:view")])),
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

export const zCreatePublicLinkResponses = z.object({
  link: zPublicLinkResponses,
  token: z.string().max(256),
  url: z.string().max(2048),
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
  submitter: zSubmitterResponses.nullable(),
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
  member: zSurveyMemberResponses.nullable(),
  role: zSurveyRoleResponses.nullable(),
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
  published_version: zSurveyVersionResponses.nullable(),
});

export const zResolveLinkResponses = z.object({
  link: zPublicLinkResponses,
  survey: zSurveyResponses.nullable(),
  published_version: zSurveyVersionResponses.nullable(),
});
