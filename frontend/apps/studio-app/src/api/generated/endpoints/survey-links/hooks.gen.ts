// This file is auto-generated — do not edit manually

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import type { CreatePublicLinkRequest, UpdatePublicLinkRequest } from "./types.gen";
import { listPublicLinks, createPublicLink, updatePublicLink, deletePublicLink } from "./requests.gen";

export const surveyLinksKeys = {
  all: () => ["survey-links"] as const,
  list: (project_id: number, survey_id: number) => [...surveyLinksKeys.all(), "list", project_id, survey_id] as const,
};

export function useListPublicLinks(project_id: number, survey_id: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: surveyLinksKeys.list(project_id, survey_id),
    queryFn: () => listPublicLinks(apiClient, project_id, survey_id),
    enabled: project_id > 0 && survey_id > 0,
  });
}

export function useCreatePublicLink(project_id: number, survey_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreatePublicLinkRequest) => createPublicLink(apiClient, project_id, survey_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyLinksKeys.list(project_id, survey_id) });
    },
  });
}

export function useUpdatePublicLink(project_id: number, survey_id: number, link_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdatePublicLinkRequest) => updatePublicLink(apiClient, project_id, survey_id, link_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyLinksKeys.list(project_id, survey_id) });
    },
  });
}

export function useDeletePublicLink(project_id: number, survey_id: number, link_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deletePublicLink(apiClient, project_id, survey_id, link_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyLinksKeys.list(project_id, survey_id) });
    },
  });
}
