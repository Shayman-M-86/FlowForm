// This file is auto-generated — do not edit manually

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import { listVersions, createVersion, copyVersionToDraft, getVersion, publishVersion, archiveVersion } from "./requests.gen";

export const surveyVersionsKeys = {
  all: () => ["survey-versions"] as const,
  list: (project_id: number, survey_id: number) => [...surveyVersionsKeys.all(), "list", project_id, survey_id] as const,
  detail: (project_id: number, survey_id: number, version_number: number) => [...surveyVersionsKeys.all(), "detail", project_id, survey_id, version_number] as const,
};

export function useListVersions(project_id: number, survey_id: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: surveyVersionsKeys.list(project_id, survey_id),
    queryFn: () => listVersions(apiClient, project_id, survey_id),
    enabled: project_id > 0 && survey_id > 0,
  });
}

export function useCreateVersion(project_id: number, survey_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => createVersion(apiClient, project_id, survey_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyVersionsKeys.list(project_id, survey_id) });
    },
  });
}

export function useCopyVersionToDraft(project_id: number, survey_id: number, version_number: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => copyVersionToDraft(apiClient, project_id, survey_id, version_number),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyVersionsKeys.list(project_id, survey_id) });
    },
  });
}

export function useGetVersion(project_id: number, survey_id: number, version_number: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: surveyVersionsKeys.detail(project_id, survey_id, version_number),
    queryFn: () => getVersion(apiClient, project_id, survey_id, version_number),
    enabled: project_id > 0 && survey_id > 0 && version_number > 0,
  });
}

export function usePublishVersion(project_id: number, survey_id: number, version_number: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => publishVersion(apiClient, project_id, survey_id, version_number),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyVersionsKeys.list(project_id, survey_id) });
    },
  });
}

export function useArchiveVersion(project_id: number, survey_id: number, version_number: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => archiveVersion(apiClient, project_id, survey_id, version_number),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyVersionsKeys.list(project_id, survey_id) });
    },
  });
}
