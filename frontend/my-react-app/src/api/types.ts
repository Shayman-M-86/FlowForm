// ── Enums ───────────────────────────────────────────────────────────────────

export type SurveyVisibility = "private" | "link_only" | "public";
export type VersionStatus = "draft" | "published" | "archived";
export type SubmissionStatus = "pending" | "stored" | "failed";
export type SubmissionChannel = "link" | "slug" | "system";
export type QuestionType = "choice" | "field" | "matching" | "rating";

// ── Projects ──────────────────────────────────────────────────────────────────

export interface ProjectOut {
  id: number;
  name: string;
  slug: string;
  created_by_user_id: number | null;
  created_at: string;
}

export interface CreateProjectRequest {
  name: string;
  slug: string;
}

// ── Survey ───────────────────────────────────────────────────────────────────

export interface SurveyOut {
  id: number;
  project_id: number;
  title: string;
  visibility: SurveyVisibility;
  public_slug: string | null;
  default_response_store_id: number | null;
  published_version_id: number | null;
  created_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface CreateSurveyRequest {
  title: string;
  visibility: SurveyVisibility;
  public_slug?: string | null;
  default_response_store_id?: number | null;
}

export interface UpdateSurveyRequest {
  title?: string;
  visibility?: SurveyVisibility;
  public_slug?: string | null;
  default_response_store_id?: number | null;
}

// ── Versions ─────────────────────────────────────────────────────────────────

export interface CompiledSchema {
  questions: QuestionSchema[];
  rules: RuleSchema[];
  scoring_rules: ScoringRuleSchema[];
}

export interface QuestionSchema {
  id: number;
  question_key: string;
  question_schema: Record<string, unknown>;
}

export interface RuleSchema {
  id: number;
  rule_key: string;
  rule_schema: Record<string, unknown>;
}

export interface ScoringRuleSchema {
  id: number;
  scoring_key: string;
  scoring_schema: Record<string, unknown>;
}

export interface SurveyVersionOut {
  id: number;
  survey_id: number;
  version_number: number;
  status: VersionStatus;
  compiled_schema: CompiledSchema | null;
  published_at: string | null;
  created_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

// ── Content ───────────────────────────────────────────────────────────────────

export interface QuestionOut {
  id: number;
  survey_version_id: number;
  question_key: string;
  question_schema: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CreateQuestionRequest {
  question_key: string;
  question_schema: Record<string, unknown>;
}

export interface UpdateQuestionRequest {
  question_key?: string;
  question_schema?: Record<string, unknown>;
}

export interface RuleOut {
  id: number;
  survey_version_id: number;
  rule_key: string;
  rule_schema: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CreateRuleRequest {
  rule_key: string;
  rule_schema: Record<string, unknown>;
}

export interface UpdateRuleRequest {
  rule_key?: string;
  rule_schema?: Record<string, unknown>;
}

export interface ScoringRuleOut {
  id: number;
  survey_version_id: number;
  scoring_key: string;
  scoring_schema: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CreateScoringRuleRequest {
  scoring_key: string;
  scoring_schema: Record<string, unknown>;
}

export interface UpdateScoringRuleRequest {
  scoring_key?: string;
  scoring_schema?: Record<string, unknown>;
}

// ── Public Links ──────────────────────────────────────────────────────────────

export interface PublicLinkOut {
  id: number;
  survey_id: number;
  token_prefix: string;
  is_active: boolean;
  assigned_email: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface CreatePublicLinkRequest {
  assigned_email?: string | null;
  expires_at?: string | null;
}

export interface UpdatePublicLinkRequest {
  is_active?: boolean;
  assigned_email?: string | null;
  expires_at?: string | null;
}

export interface CreatePublicLinkOut {
  link: PublicLinkOut;
  token: string;
  url: string;
}

export interface ListPublicLinksOut {
  links: PublicLinkOut[];
}

// ── Submissions ───────────────────────────────────────────────────────────────

export interface AnswerOut {
  id: number;
  question_key: string;
  answer_family: string;
  answer_value: Record<string, unknown>;
  created_at: string;
}

export interface CoreSubmissionOut {
  id: number;
  project_id: number;
  survey_id: number;
  survey_version_id: number;
  response_store_id: number;
  submission_channel: SubmissionChannel;
  submitted_by_user_id: number | null;
  survey_link_id: number | null;
  submitter: SubmitterOut | null;
  is_anonymous: boolean;
  status: SubmissionStatus;
  started_at: string | null;
  submitted_at: string | null;
  created_at: string;
}

export interface LinkedSubmissionOut {
  core: CoreSubmissionOut;
  answers: AnswerOut[];
}

export interface PaginatedSubmissionsOut {
  items: CoreSubmissionOut[];
  total: number;
  page: number;
  page_size: number;
}

export interface AnswerIn {
  question_key: string;
  answer_family: string;
  answer_value: Record<string, unknown>;
}

export interface LinkSubmissionRequest {
  token: string;
  survey_version_id: number;
  answers: AnswerIn[];
  metadata?: Record<string, unknown>;
  started_at?: string;
  submitted_at?: string;
}

export interface SlugSubmissionRequest {
  public_slug: string;
  survey_version_id: number;
  answers: AnswerIn[];
  metadata?: Record<string, unknown>;
  started_at?: string;
  submitted_at?: string;
}

export interface ListSubmissionsParams {
  survey_id?: number;
  status?: SubmissionStatus;
  submission_channel?: SubmissionChannel;
  page?: number;
  page_size?: number;
}

// ── Public ────────────────────────────────────────────────────────────────────

export interface PublicSurveyOut {
  survey: SurveyOut;
  published_version: SurveyVersionOut | null;
}

export interface SubmitterOut {
  id: number;
  email: string;
  display_name: string | null;
}

export interface ResolveLinkOut {
  link: PublicLinkOut;
  survey: SurveyOut | null;
  published_version: SurveyVersionOut | null;
}

export interface PaginatedPublicSurveysOut {
  items: SurveyOut[];
  total: number;
  page: number;
  page_size: number;
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export interface CurrentUserOut {
  id: number;
  auth0_user_id: string;
  email: string;
  display_name: string | null;
}

export interface BootstrapUserRequest {
  id_token: string;
}

export interface BootstrapUserOut {
  created: boolean;
  user: CurrentUserOut;
}

// ── Api executor ─────────────────────────────────────────────────────────────

export interface ApiExecutor {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body?: unknown): Promise<T>;
  patch<T>(path: string, body: unknown): Promise<T>;
  del(path: string): Promise<void>;
  getWithQuery<T>(
    path: string,
    params: Record<string, string | number | boolean | undefined>,
  ): Promise<T>;
}

// ── Errors ────────────────────────────────────────────────────────────────────

export interface ValidationErrorDetail {
  field: string;
  message: string;
  type: string;
}

export interface ApiError {
  code: string;
  message: string;
  errors?: ValidationErrorDetail[];
  details?: Record<string, unknown>;
}
