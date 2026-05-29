// This file is auto-generated — do not edit manually

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOpenApiClient } from "../../../openapi";
import type { ChangeEmailRequest, ChangeUsernameRequest, UpdateProfileRequest } from "./types.gen";
import { getMyProfile, updateMyProfile, changeEmail, changeUsername, changePassword, clearMfa, resendVerification, deleteMyAccount, getMyInvitations, acceptInvitation, declineInvitation } from "./requests.gen";

export const meKeys = {
  all: () => ["me"] as const,
};

export function useGetMyProfile() {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: meKeys.all(),
    queryFn: () => getMyProfile(apiClient),
  });
}

export function useUpdateMyProfile() {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UpdateProfileRequest) => updateMyProfile(apiClient, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: meKeys.all() });
    },
  });
}

export function useChangeEmail() {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ChangeEmailRequest) => changeEmail(apiClient, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: meKeys.all() });
    },
  });
}

export function useChangeUsername() {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ChangeUsernameRequest) => changeUsername(apiClient, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: meKeys.all() });
    },
  });
}

export function useChangePassword() {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => changePassword(apiClient),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: meKeys.all() });
    },
  });
}

export function useClearMfa() {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => clearMfa(apiClient),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: meKeys.all() });
    },
  });
}

export function useResendVerification() {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => resendVerification(apiClient),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: meKeys.all() });
    },
  });
}

export function useDeleteMyAccount() {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteMyAccount(apiClient),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: meKeys.all() });
    },
  });
}

export function useGetMyInvitations() {
  const apiClient = useOpenApiClient();
  return useQuery({
    queryKey: meKeys.all(),
    queryFn: () => getMyInvitations(apiClient),
  });
}

export function useAcceptInvitation(invitation_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => acceptInvitation(apiClient, invitation_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: meKeys.all() });
    },
  });
}

export function useDeclineInvitation(invitation_id: number) {
  const apiClient = useOpenApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => declineInvitation(apiClient, invitation_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: meKeys.all() });
    },
  });
}
