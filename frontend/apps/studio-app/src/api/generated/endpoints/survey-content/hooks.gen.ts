// This file is auto-generated — do not edit manually

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import type { CreateNodeRequest, UpdateNodeRequest } from "./types.gen";
import { listNodes, createNode, getNode, updateNode, deleteNode } from "./requests.gen";

export const surveyContentKeys = {
  all: () => ["survey-content"] as const,
  list: (project_id: number, survey_id: number, version_number: number) => [...surveyContentKeys.all(), "list", project_id, survey_id, version_number] as const,
  detail: (project_id: number, survey_id: number, version_number: number, node_id: number) => [...surveyContentKeys.all(), "detail", project_id, survey_id, version_number, node_id] as const,
};

export function useListNodes(project_id: number, survey_id: number, version_number: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: surveyContentKeys.list(project_id, survey_id, version_number),
    queryFn: () => listNodes(apiClient, project_id, survey_id, version_number),
    enabled: project_id > 0 && survey_id > 0 && version_number > 0,
  });
}

export function useCreateNode(project_id: number, survey_id: number, version_number: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateNodeRequest) => createNode(apiClient, project_id, survey_id, version_number, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyContentKeys.list(project_id, survey_id, version_number) });
    },
  });
}

export function useGetNode(project_id: number, survey_id: number, version_number: number, node_id: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: surveyContentKeys.detail(project_id, survey_id, version_number, node_id),
    queryFn: () => getNode(apiClient, project_id, survey_id, version_number, node_id),
    enabled: project_id > 0 && survey_id > 0 && version_number > 0 && node_id > 0,
  });
}

export function useUpdateNode(project_id: number, survey_id: number, version_number: number, node_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateNodeRequest) => updateNode(apiClient, project_id, survey_id, version_number, node_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyContentKeys.list(project_id, survey_id, version_number) });
    },
  });
}

export function useDeleteNode(project_id: number, survey_id: number, version_number: number, node_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteNode(apiClient, project_id, survey_id, version_number, node_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyContentKeys.list(project_id, survey_id, version_number) });
    },
  });
}
