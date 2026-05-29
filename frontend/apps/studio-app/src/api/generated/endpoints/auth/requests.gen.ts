// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";
import type { BootstrapUserRequest, BootstrapUserResponses } from "./types.gen";

export async function bootstrapUser(apiClient: OpenApiFetchClient, body: BootstrapUserRequest): Promise<BootstrapUserResponses> {
  const { data, error } = await apiClient.POST(`/api/v1/auth/bootstrap-user`, { body: body as never });
  if (error) throw error;
  return data;
}
