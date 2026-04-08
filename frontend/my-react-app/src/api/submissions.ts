import type {
  ApiExecutor,
  CoreSubmissionOut,
  CreateSubmissionRequest,
  LinkedSubmissionOut,
  ListSubmissionsParams,
  PaginatedSubmissionsOut,
} from "./types";

export function listSubmissions(
  api: ApiExecutor,
  projectId: number,
  params: ListSubmissionsParams = {},
): Promise<PaginatedSubmissionsOut> {
  return api.getWithQuery<PaginatedSubmissionsOut>(
    `/api/v1/projects/${projectId}/submissions`,
    params as Record<string, string | number | boolean | undefined>,
  );
}

export function getSubmission(
  api: ApiExecutor,
  projectId: number,
  submissionId: number,
  includeAnswers = false,
): Promise<LinkedSubmissionOut> {
  return api.getWithQuery<LinkedSubmissionOut>(
    `/api/v1/projects/${projectId}/submissions/${submissionId}`,
    { include_answers: includeAnswers },
  );
}

export function createSubmission(
  api: ApiExecutor,
  projectId: number,
  surveyId: number,
  data: CreateSubmissionRequest,
): Promise<LinkedSubmissionOut> {
  return api.post<LinkedSubmissionOut>(
    `/api/v1/projects/${projectId}/surveys/${surveyId}/submissions`,
    data,
  );
}

export function getSubmissionCore(
  api: ApiExecutor,
  projectId: number,
  submissionId: number,
): Promise<CoreSubmissionOut> {
  return api.get<CoreSubmissionOut>(
    `/api/v1/projects/${projectId}/submissions/${submissionId}`,
  );
}
