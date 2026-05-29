// This file is auto-generated — do not edit manually

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import type { LinkSubmissionRequest, SlugSubmissionRequest } from "./types.gen";
import { createSlugSubmission, createLinkSubmission } from "./requests.gen";

export const publicSubmissionsKeys = {
  all: () => ["public-submissions"] as const,
};

export function useCreateSlugSubmission() {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: SlugSubmissionRequest) => createSlugSubmission(apiClient, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: publicSubmissionsKeys.all() });
    },
  });
}

export function useCreateLinkSubmission() {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: LinkSubmissionRequest) => createLinkSubmission(apiClient, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: publicSubmissionsKeys.all() });
    },
  });
}
