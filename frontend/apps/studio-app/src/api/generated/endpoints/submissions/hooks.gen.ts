// This file is auto-generated — do not edit manually

import { useQuery } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import { listSubmissions, getSubmission } from "./requests.gen";

export const submissionsKeys = {
  all: () => ["submissions"] as const,
  list: (project_id: number) => [...submissionsKeys.all(), "list", project_id] as const,
  detail: (project_id: number, submission_id: number) => [...submissionsKeys.all(), "detail", project_id, submission_id] as const,
};

export function useListSubmissions(project_id: number, query?: { survey_id?: number | null; status?: "pending" | "stored" | "failed" | null; submission_channel?: "link" | "slug" | "system" | null; page?: number; page_size?: number }) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: submissionsKeys.list(project_id),
    queryFn: () => listSubmissions(apiClient, project_id, query),
    enabled: project_id > 0,
  });
}

export function useGetSubmission(project_id: number, submission_id: number, query?: { include_answers?: boolean; resolve_identity?: boolean }) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: submissionsKeys.detail(project_id, submission_id),
    queryFn: () => getSubmission(apiClient, project_id, submission_id, query),
    enabled: project_id > 0 && submission_id > 0,
  });
}
