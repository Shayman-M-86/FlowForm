import type { OpenApiFetchClient } from '../openapi'
import type {
  ChangeEmailRequest,
  ChangeUsernameRequest,
  CurrentUserOut,
  CurrentUserProfileOut,
  PasswordChangeTicketOut,
  UpdateProfileRequest,
} from './types'

export async function getMyProfile(apiClient: OpenApiFetchClient): Promise<CurrentUserProfileOut> {
  const { data, error } = await apiClient.GET('/api/v1/me/profile')
  if (error) throw error
  return data
}

export async function updateMyProfile(
  apiClient: OpenApiFetchClient,
  body: UpdateProfileRequest,
): Promise<CurrentUserOut> {
  const { data, error } = await apiClient.PATCH('/api/v1/me/profile', { body })
  if (error) throw error
  return data
}

export async function changeEmail(
  apiClient: OpenApiFetchClient,
  body: ChangeEmailRequest,
): Promise<void> {
  const { error } = await apiClient.POST('/api/v1/me/change-email', { body })
  if (error) throw error
}

export async function changeUsername(
  apiClient: OpenApiFetchClient,
  body: ChangeUsernameRequest,
): Promise<void> {
  const { error } = await apiClient.POST('/api/v1/me/change-username', { body })
  if (error) throw error
}

export async function changePassword(apiClient: OpenApiFetchClient): Promise<PasswordChangeTicketOut> {
  const { data, error } = await apiClient.POST('/api/v1/me/change-password', {})
  if (error) throw error
  return data
}

export async function clearMfa(apiClient: OpenApiFetchClient): Promise<void> {
  const { error } = await apiClient.POST('/api/v1/me/clear-mfa', {})
  if (error) throw error
}

export async function resendVerification(apiClient: OpenApiFetchClient): Promise<void> {
  const { error } = await apiClient.POST('/api/v1/me/resend-verification', {})
  if (error) throw error
}

export async function deleteMyAccount(apiClient: OpenApiFetchClient): Promise<void> {
  const { error } = await apiClient.DELETE('/api/v1/me')
  if (error) throw error
}
