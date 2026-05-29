// This file is auto-generated — do not edit manually

import { useQuery } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import { resolveLink } from "./requests.gen";

export const publicLinksKeys = {
  all: () => ["public-links"] as const,
  list: () => [...publicLinksKeys.all(), "list"] as const,
};

export function useResolveLink(query: { token: string }) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: publicLinksKeys.list(),
    queryFn: () => resolveLink(apiClient, query),
  });
}
