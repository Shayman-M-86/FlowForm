// This file is auto-generated — do not edit manually

import { useQuery } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import { healthCheck, readinessCheck } from "./requests.gen";

export const healthKeys = {
  all: () => ["health"] as const,
  list: () => [...healthKeys.all(), "list"] as const,
};

export function useHealthCheck() {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: healthKeys.list(),
    queryFn: () => healthCheck(apiClient),
  });
}

export function useReadinessCheck() {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: healthKeys.list(),
    queryFn: () => readinessCheck(apiClient),
  });
}
