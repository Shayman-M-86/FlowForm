// This file is auto-generated — do not edit manually

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import type { CreateSurveyRoleRequest, UpdateSurveyRoleRequest } from "./types.gen";
import { listSurveyRoles, createSurveyRole, updateSurveyRole, deleteSurveyRole } from "./requests.gen";

export const surveyRolesKeys = {
  all: () => ["survey-roles"] as const,
  list: (project_id: number) => [...surveyRolesKeys.all(), "list", project_id] as const,
};

export function useListSurveyRoles(project_id: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: surveyRolesKeys.list(project_id),
    queryFn: () => listSurveyRoles(apiClient, project_id),
    enabled: project_id > 0,
  });
}

export function useCreateSurveyRole(project_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateSurveyRoleRequest) => createSurveyRole(apiClient, project_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyRolesKeys.list(project_id) });
    },
  });
}

export function useUpdateSurveyRole(project_id: number, role_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateSurveyRoleRequest) => updateSurveyRole(apiClient, project_id, role_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyRolesKeys.list(project_id) });
    },
  });
}

export function useDeleteSurveyRole(project_id: number, role_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteSurveyRole(apiClient, project_id, role_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyRolesKeys.list(project_id) });
    },
  });
}
