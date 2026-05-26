import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOpenApiClient } from '../openapi'
import {
  changeEmail,
  changePassword,
  changeUsername,
  clearMfa,
  deleteMyAccount,
  getMyProfile,
  resendVerification,
  updateMyProfile,
} from './requests'
import type { ChangeEmailRequest, ChangeUsernameRequest, CurrentUserProfileOut, UpdateProfileRequest } from './types'

export const meKeys = {
  profile: () => ['me', 'profile'] as const,
}

export function useMyProfile() {
  const apiClient = useOpenApiClient()

  return useQuery({
    queryKey: meKeys.profile(),
    queryFn: () => getMyProfile(apiClient),
  })
}

export function useUpdateProfile() {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: UpdateProfileRequest) => updateMyProfile(apiClient, body),
    onSuccess: (updatedUser) => {
      queryClient.setQueryData<CurrentUserProfileOut | undefined>(meKeys.profile(), (profile) => (
        profile
          ? {
              ...profile,
              id: updatedUser.id,
              auth0_user_id: updatedUser.auth0_user_id,
              email: updatedUser.email,
              display_name: updatedUser.display_name,
            }
          : profile
      ))
      void queryClient.invalidateQueries({ queryKey: meKeys.profile() })
    },
  })
}

export function useChangeEmail() {
  const apiClient = useOpenApiClient()

  return useMutation({
    mutationFn: (body: ChangeEmailRequest) => changeEmail(apiClient, body),
  })
}

export function useChangeUsername() {
  const apiClient = useOpenApiClient()

  return useMutation({
    mutationFn: (body: ChangeUsernameRequest) => changeUsername(apiClient, body),
  })
}

export function useChangePassword() {
  const apiClient = useOpenApiClient()

  return useMutation({
    mutationFn: () => changePassword(apiClient),
  })
}

export function useClearMfa() {
  const apiClient = useOpenApiClient()

  return useMutation({
    mutationFn: () => clearMfa(apiClient),
  })
}

export function useResendVerification() {
  const apiClient = useOpenApiClient()

  return useMutation({
    mutationFn: () => resendVerification(apiClient),
  })
}

export function useDeleteAccount() {
  const apiClient = useOpenApiClient()

  return useMutation({
    mutationFn: () => deleteMyAccount(apiClient),
  })
}
