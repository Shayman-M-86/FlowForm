// This file is auto-generated — do not edit manually

import { useQuery } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import { listPublicSurveys, getPublicSurvey } from "./requests.gen";

export const publicKeys = {
  all: () => ["public"] as const,
  list: () => [...publicKeys.all(), "list"] as const,
  detail: (public_slug: string) => [...publicKeys.all(), "detail", public_slug] as const,
};

export function useListPublicSurveys(query?: { page?: number; page_size?: number }) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: publicKeys.list(),
    queryFn: () => listPublicSurveys(apiClient, query),
  });
}

export function useGetPublicSurvey(public_slug: string) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: publicKeys.detail(public_slug),
    queryFn: () => getPublicSurvey(apiClient, public_slug),
    enabled: !!public_slug,
  });
}
