// This file is auto-generated — do not edit manually

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import type { CreateSurveyRequest, UpdateSurveyRequest } from "./types.gen";
import { listSurveys, createSurvey, getSurvey, updateSurvey, deleteSurvey } from "./requests.gen";

export const surveysKeys = {
  all: () => ["surveys"] as const,
  list: (project_id: number) => [...surveysKeys.all(), "list", project_id] as const,
  detail: (project_id: number, survey_id: number) => [...surveysKeys.all(), "detail", project_id, survey_id] as const,
};

export function useListSurveys(project_id: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: surveysKeys.list(project_id),
    queryFn: () => listSurveys(apiClient, project_id),
    enabled: project_id > 0,
  });
}

export function useCreateSurvey(project_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateSurveyRequest) => createSurvey(apiClient, project_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveysKeys.list(project_id) });
    },
  });
}

export function useGetSurvey(project_id: number, survey_id: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: surveysKeys.detail(project_id, survey_id),
    queryFn: () => getSurvey(apiClient, project_id, survey_id),
    enabled: project_id > 0 && survey_id > 0,
  });
}

export function useUpdateSurvey(project_id: number, survey_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateSurveyRequest) => updateSurvey(apiClient, project_id, survey_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveysKeys.list(project_id) });
    },
  });
}

export function useDeleteSurvey(project_id: number, survey_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteSurvey(apiClient, project_id, survey_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveysKeys.list(project_id) });
    },
  });
}
