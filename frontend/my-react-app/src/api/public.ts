import { get, getWithQuery, post } from "./client";
import type {
  LinkedSubmissionOut,
  PublicSubmissionRequest,
  PublicSurveyOut,
  ResolveLinkOut,
} from "./types";

export function getPublicSurvey(publicSlug: string): Promise<PublicSurveyOut> {
  return get(`/api/v1/public/surveys/${publicSlug}`);
}

export function resolveToken(token: string): Promise<ResolveLinkOut> {
  return getWithQuery("/api/v1/public/links/resolve", { token });
}

export function createPublicSubmission(
  data: PublicSubmissionRequest,
): Promise<LinkedSubmissionOut> {
  return post("/api/v1/public/submissions", data);
}
