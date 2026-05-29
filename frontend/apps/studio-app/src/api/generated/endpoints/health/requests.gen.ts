// This file is auto-generated — do not edit manually

import type { OpenApiFetchClient } from "../../../openapi";

export async function healthCheck(apiClient: OpenApiFetchClient): Promise<void> {
  const { error } = await apiClient.GET(`/api/v1/health`);
  if (error) throw error;
}

export async function readinessCheck(apiClient: OpenApiFetchClient): Promise<void> {
  const { error } = await apiClient.GET(`/api/v1/health/ready`);
  if (error) throw error;
}
