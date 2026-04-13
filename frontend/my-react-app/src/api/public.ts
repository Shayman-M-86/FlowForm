import { get, getWithQuery, post } from "./client";
import type {
  LinkSubmissionRequest,
  LinkedSubmissionOut,
  PaginatedPublicSurveysOut,
  PublicSurveyOut,
  ResolveLinkOut,
  SlugSubmissionRequest,
} from "./types";

export function listPublicSurveys(page = 1, pageSize = 20): Promise<PaginatedPublicSurveysOut> {
  return getWithQuery("/api/v1/public/surveys", { page, page_size: pageSize });
}

export function getPublicSurvey(publicSlug: string): Promise<PublicSurveyOut> {
  return get(`/api/v1/public/surveys/${publicSlug}`);
}

/** Resolve a private link token — requires a bearer token. */
export function resolveToken(token: string, authHeaders: HeadersInit): Promise<ResolveLinkOut> {
  return getWithQuery("/api/v1/public/links/resolve", { token }, authHeaders);
}

export function createSlugSubmission(
  data: SlugSubmissionRequest,
  authHeaders?: HeadersInit,
): Promise<LinkedSubmissionOut> {
  return post("/api/v1/public/submissions/slug", data, authHeaders);
}

export function createLinkSubmission(
  data: LinkSubmissionRequest,
  authHeaders: HeadersInit,
): Promise<LinkedSubmissionOut> {
  return post("/api/v1/public/submissions/link", data, authHeaders);
}
