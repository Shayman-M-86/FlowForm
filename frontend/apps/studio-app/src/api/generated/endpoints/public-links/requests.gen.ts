// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { ResolveLinkResponses } from "./types.gen";

export async function resolveLink(apiClient: OpenApiFetchClient, query: { token: string }): Promise<ResolveLinkResponses> {
  const { data, error } = await apiClient.GET(`/api/v1/public/links/resolve`, { params: { query: query ?? {} } });
  if (error) throw error;
  return data;
}
