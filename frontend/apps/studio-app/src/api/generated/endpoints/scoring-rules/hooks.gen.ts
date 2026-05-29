// This file is auto-generated — do not edit manually

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import type { CreateScoringRuleRequest, UpdateScoringRuleRequest } from "./types.gen";
import { listScoringRules, createScoringRule, updateScoringRule, deleteScoringRule } from "./requests.gen";

export const scoringRulesKeys = {
  all: () => ["scoring-rules"] as const,
  list: (project_id: number, survey_id: number, version_number: number) => [...scoringRulesKeys.all(), "list", project_id, survey_id, version_number] as const,
};

export function useListScoringRules(project_id: number, survey_id: number, version_number: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: scoringRulesKeys.list(project_id, survey_id, version_number),
    queryFn: () => listScoringRules(apiClient, project_id, survey_id, version_number),
    enabled: project_id > 0 && survey_id > 0 && version_number > 0,
  });
}

export function useCreateScoringRule(project_id: number, survey_id: number, version_number: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateScoringRuleRequest) => createScoringRule(apiClient, project_id, survey_id, version_number, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: scoringRulesKeys.list(project_id, survey_id, version_number) });
    },
  });
}

export function useUpdateScoringRule(project_id: number, survey_id: number, version_number: number, scoring_rule_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateScoringRuleRequest) => updateScoringRule(apiClient, project_id, survey_id, version_number, scoring_rule_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: scoringRulesKeys.list(project_id, survey_id, version_number) });
    },
  });
}

export function useDeleteScoringRule(project_id: number, survey_id: number, version_number: number, scoring_rule_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteScoringRule(apiClient, project_id, survey_id, version_number, scoring_rule_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: scoringRulesKeys.list(project_id, survey_id, version_number) });
    },
  });
}
