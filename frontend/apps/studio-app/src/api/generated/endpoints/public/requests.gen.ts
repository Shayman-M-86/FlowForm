// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { PaginatedPublicSurveysResponses, PublicSurveyResponses } from "./types.gen";

export async function listPublicSurveys(apiClient: OpenApiFetchClient, query?: { page?: number; page_size?: number }): Promise<PaginatedPublicSurveysResponses> {
  const { data, error } = await apiClient.GET(`/api/v1/public/surveys`, { params: { query: query ?? {} } });
  if (error) throw error;
  return data;
}

export async function getPublicSurvey(apiClient: OpenApiFetchClient, public_slug: string): Promise<PublicSurveyResponses> {
  const { data, error } = await apiClient.GET(`/api/v1/public/surveys/{public_slug}`, { params: { path: { public_slug } } });
  if (error) throw error;
  return data;
}
