import { get, getWithQuery, post } from "./client";
import type {
  CoreSubmissionOut,
  CreateSubmissionRequest,
  LinkedSubmissionOut,
  ListSubmissionsParams,
  PaginatedSubmissionsOut,
} from "./types";

export function listSubmissions(
  projectId: number,
  params: ListSubmissionsParams = {},
): Promise<PaginatedSubmissionsOut> {
  return getWithQuery(`/api/v1/projects/${projectId}/submissions`, params as Record<string, string | number | boolean | undefined>);
}

export function getSubmission(
  projectId: number,
  submissionId: number,
  includeAnswers = false,
): Promise<LinkedSubmissionOut> {
  return getWithQuery(
    `/api/v1/projects/${projectId}/submissions/${submissionId}`,
    { include_answers: includeAnswers },
  );
}

export function createSubmission(
  projectId: number,
  surveyId: number,
  data: CreateSubmissionRequest,
): Promise<LinkedSubmissionOut> {
  return post(
    `/api/v1/projects/${projectId}/surveys/${surveyId}/submissions`,
    data,
  );
}

export function getSubmissionCore(
  projectId: number,
  submissionId: number,
): Promise<CoreSubmissionOut> {
  return get(`/api/v1/projects/${projectId}/submissions/${submissionId}`);
}
