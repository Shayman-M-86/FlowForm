// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { LinkSubmissionRequest, LinkedSubmissionResponses, SlugSubmissionRequest } from "./types.gen";

export async function createSlugSubmission(apiClient: OpenApiFetchClient, body: SlugSubmissionRequest): Promise<LinkedSubmissionResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/public/submissions/slug`, { body: body as never });
  if (error) throw error;
  return data;
}

export async function createLinkSubmission(apiClient: OpenApiFetchClient, body: LinkSubmissionRequest): Promise<LinkedSubmissionResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/public/submissions/link`, { body: body as never });
  if (error) throw error;
  return data;
}
