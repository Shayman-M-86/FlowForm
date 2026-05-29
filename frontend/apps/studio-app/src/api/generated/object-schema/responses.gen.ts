// This file is auto-generated — do not edit manually

export interface CurrentUserResponses {
  id: number;
  auth0_user_id: string;
  email: string;
  display_name: string | null;
}

export const CurrentUserResponsesConstraints = {
  auth0_user_id: { maxLength: 255 },
  email: { maxLength: 254 },
  display_name: { maxLength: 100 },
} as const;

export interface ProjectResponses {
  id: number;
  name: string;
  slug: string;
  created_by_user_id: number | null;
  created_at: string;
}

export const ProjectResponsesConstraints = {
  name: { maxLength: 100 },
  slug: { maxLength: 80 },
  created_at: { maxLength: 35 },
} as const;

export interface BootstrapUserResponses {
  created: boolean;
  user: CurrentUserResponses;
  default_project: ProjectResponses | null;
}

export interface CurrentUserProfileResponses {
  id: number;
  auth0_user_id: string;
  email: string;
  display_name: string | null;
  email_verified: boolean;
}

export const CurrentUserProfileResponsesConstraints = {
  auth0_user_id: { maxLength: 255 },
  email: { maxLength: 254 },
  display_name: { maxLength: 100 },
} as const;

export interface PasswordChangeTicketResponses {
  ticket_url: string;
}

export const PasswordChangeTicketResponsesConstraints = {
  ticket_url: { maxLength: 2048 },
} as const;

export interface ProjectInvitationResponses {
  id: number;
  project_id: number;
  project_name: string | null;
  invited_email: string;
  invite_message: string | null;
  invited_by_user_id: number | null;
  invited_by_display: string | null;
  role_id: number | null;
  status: "pending" | "accepted" | "declined" | "revoked";
  expires_at: string | null;
  accepted_at: string | null;
  created_at: string;
}

export const ProjectInvitationResponsesConstraints = {
  invited_email: { maxLength: 254 },
  invite_message: { maxLength: 500 },
  status: { maxLength: 8 },
  expires_at: { maxLength: 35 },
  accepted_at: { maxLength: 35 },
  created_at: { maxLength: 35 },
} as const;

export interface MemberUserResponses {
  id: number;
  email: string;
  display_name: string | null;
}

export const MemberUserResponsesConstraints = {
  email: { maxLength: 254 },
  display_name: { maxLength: 100 },
} as const;

export interface ProjectMemberResponses {
  id: number;
  user_id: number;
  project_id: number;
  role_id: number | null;
  status: "active" | "suspended";
  created_at: string;
  user: MemberUserResponses;
}

export const ProjectMemberResponsesConstraints = {
  status: { maxLength: 9 },
  created_at: { maxLength: 35 },
} as const;

export interface NodeResponses {
  id: number;
  survey_version_id: number;
  question_key: string;
  sort_key: number;
  node_type: "question" | "rule";
  question_schema: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export const NodeResponsesConstraints = {
  question_key: { maxLength: 128 },
  node_type: { maxLength: 8 },
  created_at: { maxLength: 35 },
  updated_at: { maxLength: 35 },
} as const;

export interface ScoringRuleResponses {
  id: number;
  survey_version_id: number;
  scoring_key: string;
  scoring_schema: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export const ScoringRuleResponsesConstraints = {
  scoring_key: { maxLength: 128 },
  created_at: { maxLength: 35 },
  updated_at: { maxLength: 35 },
} as const;

export interface MyProjectPermissionsResponses {
  permissions: ("project:edit" | "project:delete" | "project:manage_members" | "project:manage_roles" | "survey:view" | "survey:create" | "survey:edit" | "survey:delete" | "survey:publish" | "survey:archive" | "submission:view")[];
}

export interface PublicLinkResponses {
  id: number;
  survey_id: number;
  name: string;
  token_prefix: string;
  is_active: boolean;
  requires_auth: boolean;
  assigned_email: string | null;
  expires_at: string | null;
  used_at: string | null;
  created_at: string;
}

export const PublicLinkResponsesConstraints = {
  name: { maxLength: 120 },
  token_prefix: { maxLength: 32 },
  assigned_email: { maxLength: 254 },
  expires_at: { maxLength: 35 },
  used_at: { maxLength: 35 },
  created_at: { maxLength: 35 },
} as const;

export interface ListPublicLinksResponses {
  links: PublicLinkResponses[];
}

export interface CreatePublicLinkResponses {
  link: PublicLinkResponses;
  token: string;
  url: string;
}

export const CreatePublicLinkResponsesConstraints = {
  token: { maxLength: 256 },
  url: { maxLength: 2048 },
} as const;

export interface ProjectRoleResponses {
  id: number;
  project_id: number;
  name: string;
  description: string | null;
  is_system_role: boolean;
  permissions: ("project:edit" | "project:delete" | "project:manage_members" | "project:manage_roles" | "survey:view" | "survey:create" | "survey:edit" | "survey:delete" | "survey:publish" | "survey:archive" | "submission:view")[];
  created_at: string;
}

export const ProjectRoleResponsesConstraints = {
  name: { maxLength: 120 },
  description: { maxLength: 500 },
  permissions: { maxItems: 11 },
  created_at: { maxLength: 35 },
} as const;

export interface SubmitterResponses {
  id: number;
  email: string;
  display_name: string | null;
}

export const SubmitterResponsesConstraints = {
  email: { maxLength: 254 },
  display_name: { maxLength: 100 },
} as const;

export interface CoreSubmissionResponses {
  id: number;
  project_id: number;
  survey_id: number;
  survey_version_id: number;
  response_store_id: number;
  submission_channel: "link" | "slug" | "system";
  submitted_by_user_id: number | null;
  survey_link_id: number | null;
  submitter: SubmitterResponses | null;
  is_anonymous: boolean;
  status: "pending" | "stored" | "failed";
  started_at: string | null;
  submitted_at: string | null;
  created_at: string;
}

export const CoreSubmissionResponsesConstraints = {
  submission_channel: { maxLength: 6 },
  status: { maxLength: 7 },
  started_at: { maxLength: 35 },
  submitted_at: { maxLength: 35 },
  created_at: { maxLength: 35 },
} as const;

export interface PaginatedSubmissionsResponses {
  items: CoreSubmissionResponses[];
  total: number;
  page: number;
  page_size: number;
}

export const PaginatedSubmissionsResponsesConstraints = {
  items: { maxItems: 100 },
} as const;

export interface AnswerResponses {
  id: number;
  question_key: string;
  answer_family: "choice" | "field" | "matching" | "rating";
  answer_value: Record<string, unknown>;
  created_at: string;
}

export const AnswerResponsesConstraints = {
  question_key: { maxLength: 128 },
  answer_family: { maxLength: 8 },
  created_at: { maxLength: 35 },
} as const;

export interface LinkedSubmissionResponses {
  core: CoreSubmissionResponses;
  answers: AnswerResponses[];
}

export const LinkedSubmissionResponsesConstraints = {
  answers: { maxItems: 50 },
} as const;

export interface SurveyMemberResponses {
  id: number;
  user_id: number;
  project_id: number;
  role_id: number | null;
  status: string;
}

export interface SurveyRoleResponses {
  id: number;
  project_id: number;
  name: string;
  description: string | null;
  permissions: ("survey:view" | "survey:create" | "survey:edit" | "survey:delete" | "survey:publish" | "survey:archive" | "submission:view")[];
  created_at: string;
}

export const SurveyRoleResponsesConstraints = {
  name: { maxLength: 120 },
  description: { maxLength: 500 },
  permissions: { maxItems: 7 },
  created_at: { maxLength: 35 },
} as const;

export interface SurveyMemberRoleResponses {
  project_id: number;
  survey_id: number;
  membership_id: number;
  role_id: number;
  created_at: string;
  member: SurveyMemberResponses | null;
  role: SurveyRoleResponses | null;
}

export const SurveyMemberRoleResponsesConstraints = {
  created_at: { maxLength: 35 },
} as const;

export interface SurveyResponses {
  id: number;
  project_id: number;
  title: string;
  visibility: "private" | "link_only" | "public";
  public_slug: string | null;
  default_response_store_id: number | null;
  published_version_id: number | null;
  created_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export const SurveyResponsesConstraints = {
  title: { maxLength: 200 },
  visibility: { maxLength: 9 },
  public_slug: { maxLength: 80 },
  created_at: { maxLength: 35 },
  updated_at: { maxLength: 35 },
} as const;

export interface SurveyVersionResponses {
  id: number;
  survey_id: number;
  version_number: number;
  status: "draft" | "published" | "archived";
  compiled_schema: Record<string, unknown> | null;
  published_at: string | null;
  created_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export const SurveyVersionResponsesConstraints = {
  status: { maxLength: 9 },
  published_at: { maxLength: 35 },
  created_at: { maxLength: 35 },
  updated_at: { maxLength: 35 },
} as const;

export interface PaginatedPublicSurveysResponses {
  items: SurveyResponses[];
  total: number;
  page: number;
  page_size: number;
}

export const PaginatedPublicSurveysResponsesConstraints = {
  items: { maxItems: 100 },
} as const;

export interface PublicSurveyResponses {
  survey: SurveyResponses;
  published_version: SurveyVersionResponses | null;
}

export interface ResolveLinkResponses {
  link: PublicLinkResponses;
  survey: SurveyResponses | null;
  published_version: SurveyVersionResponses | null;
}
