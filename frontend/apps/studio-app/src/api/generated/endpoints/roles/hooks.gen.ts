// This file is auto-generated — do not edit manually

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import type { CreateProjectRoleRequest, UpdateProjectRoleRequest } from "./types.gen";
import { listRoles, createRole, updateRole, deleteRole } from "./requests.gen";

export const rolesKeys = {
  all: () => ["roles"] as const,
  list: (project_id: number) => [...rolesKeys.all(), "list", project_id] as const,
};

export function useListRoles(project_id: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: rolesKeys.list(project_id),
    queryFn: () => listRoles(apiClient, project_id),
    enabled: project_id > 0,
  });
}

export function useCreateRole(project_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateProjectRoleRequest) => createRole(apiClient, project_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: rolesKeys.list(project_id) });
    },
  });
}

export function useUpdateRole(project_id: number, role_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateProjectRoleRequest) => updateRole(apiClient, project_id, role_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: rolesKeys.list(project_id) });
    },
  });
}

export function useDeleteRole(project_id: number, role_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteRole(apiClient, project_id, role_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: rolesKeys.list(project_id) });
    },
  });
}
