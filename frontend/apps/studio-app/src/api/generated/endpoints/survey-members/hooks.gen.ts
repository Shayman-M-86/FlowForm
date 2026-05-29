// This file is auto-generated — do not edit manually

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import type { AssignSurveyMemberRoleRequest, UpdateSurveyMemberRoleRequest } from "./types.gen";
import { listSurveyMembers, assignSurveyMemberRole, updateSurveyMemberRole, removeSurveyMemberRole } from "./requests.gen";

export const surveyMembersKeys = {
  all: () => ["survey-members"] as const,
  list: (project_id: number, survey_id: number) => [...surveyMembersKeys.all(), "list", project_id, survey_id] as const,
};

export function useListSurveyMembers(project_id: number, survey_id: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: surveyMembersKeys.list(project_id, survey_id),
    queryFn: () => listSurveyMembers(apiClient, project_id, survey_id),
    enabled: project_id > 0 && survey_id > 0,
  });
}

export function useAssignSurveyMemberRole(project_id: number, survey_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: AssignSurveyMemberRoleRequest) => assignSurveyMemberRole(apiClient, project_id, survey_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyMembersKeys.list(project_id, survey_id) });
    },
  });
}

export function useUpdateSurveyMemberRole(project_id: number, survey_id: number, membership_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateSurveyMemberRoleRequest) => updateSurveyMemberRole(apiClient, project_id, survey_id, membership_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyMembersKeys.list(project_id, survey_id) });
    },
  });
}

export function useRemoveSurveyMemberRole(project_id: number, survey_id: number, membership_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => removeSurveyMemberRole(apiClient, project_id, survey_id, membership_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyMembersKeys.list(project_id, survey_id) });
    },
  });
}
