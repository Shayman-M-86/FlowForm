// This file is auto-generated — do not edit manually

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import type { CreateProjectRequest, UpdateProjectRequest } from "./types.gen";
import { listProjects, createProject, getProject, updateProject, deleteProject, getMyProjectPermissions } from "./requests.gen";

export const projectsKeys = {
  all: () => ["projects"] as const,
  list: () => [...projectsKeys.all(), "list"] as const,
  detail: (project_id: number) => [...projectsKeys.all(), "detail", project_id] as const,
};

export function useListProjects() {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: projectsKeys.list(),
    queryFn: () => listProjects(apiClient),
  });
}

export function useCreateProject() {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateProjectRequest) => createProject(apiClient, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectsKeys.list() });
    },
  });
}

export function useGetProject(project_id: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: projectsKeys.detail(project_id),
    queryFn: () => getProject(apiClient, project_id),
    enabled: project_id > 0,
  });
}

export function useUpdateProject(project_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateProjectRequest) => updateProject(apiClient, project_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectsKeys.list() });
    },
  });
}

export function useDeleteProject(project_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteProject(apiClient, project_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: projectsKeys.list() });
    },
  });
}

export function useGetMyProjectPermissions(project_id: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: projectsKeys.detail(project_id),
    queryFn: () => getMyProjectPermissions(apiClient, project_id),
    enabled: project_id > 0,
  });
}
