import type {
  ApiExecutor,
  CoreSubmissionOut,
  LinkedSubmissionOut,
  ListSubmissionsParams,
  PaginatedSubmissionsOut,
  ProjectRef,
} from "./types";

export function listSubmissions(
  api: ApiExecutor,
  projectId: ProjectRef,
  params: ListSubmissionsParams = {},
): Promise<PaginatedSubmissionsOut> {
  return api.getWithQuery<PaginatedSubmissionsOut>(
    `/api/v1/projects/${projectId}/submissions`,
    params as Record<string, string | number | boolean | undefined>,
  );
}

export function getSubmission(
  api: ApiExecutor,
  projectId: ProjectRef,
  submissionId: number,
  includeAnswers = false,
): Promise<LinkedSubmissionOut> {
  return api.getWithQuery<LinkedSubmissionOut>(
    `/api/v1/projects/${projectId}/submissions/${submissionId}`,
    { include_answers: includeAnswers },
  );
}

export function getSubmissionCore(
  api: ApiExecutor,
  projectId: ProjectRef,
  submissionId: number,
): Promise<CoreSubmissionOut> {
  return api.get<CoreSubmissionOut>(
    `/api/v1/projects/${projectId}/submissions/${submissionId}`,
  );
}
