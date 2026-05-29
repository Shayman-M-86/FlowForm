// This file is auto-generated — do not edit manually

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import type { SendInvitationRequest, UpdateMemberRequest } from "./types.gen";
import { listMembers, listInvitations, sendInvitation, revokeInvitation, updateMember, removeMember } from "./requests.gen";

export const membersKeys = {
  all: () => ["members"] as const,
  list: (project_id: number) => [...membersKeys.all(), "list", project_id] as const,
};

export function useListMembers(project_id: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: membersKeys.list(project_id),
    queryFn: () => listMembers(apiClient, project_id),
    enabled: project_id > 0,
  });
}

export function useListInvitations(project_id: number) {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: membersKeys.list(project_id),
    queryFn: () => listInvitations(apiClient, project_id),
    enabled: project_id > 0,
  });
}

export function useSendInvitation(project_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: SendInvitationRequest) => sendInvitation(apiClient, project_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: membersKeys.list(project_id) });
    },
  });
}

export function useRevokeInvitation(project_id: number, invitation_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => revokeInvitation(apiClient, project_id, invitation_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: membersKeys.list(project_id) });
    },
  });
}

export function useUpdateMember(project_id: number, membership_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateMemberRequest) => updateMember(apiClient, project_id, membership_id, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: membersKeys.list(project_id) });
    },
  });
}

export function useRemoveMember(project_id: number, membership_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => removeMember(apiClient, project_id, membership_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: membersKeys.list(project_id) });
    },
  });
}
