// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { LinkedSubmissionResponses, PaginatedSubmissionsResponses } from "./types.gen";

export async function listSubmissions(apiClient: OpenApiFetchClient, project_id: number, query?: { survey_id?: number | null; status?: "pending" | "stored" | "failed" | null; submission_channel?: "link" | "slug" | "system" | null; page?: number; page_size?: number }): Promise<PaginatedSubmissionsResponses> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/submissions`, { params: { path: { project_id }, query: query ?? {} } });
  if (error) throw error;
  return data;
}

export async function getSubmission(apiClient: OpenApiFetchClient, project_id: number, submission_id: number, query?: { include_answers?: boolean; resolve_identity?: boolean }): Promise<LinkedSubmissionResponses> {
  const { data, error } = await apiClient.GET(`/api/v1/projects/{project_id}/submissions/{submission_id}`, { params: { path: { project_id, submission_id }, query: query ?? {} } });
  if (error) throw error;
  return data;
}
