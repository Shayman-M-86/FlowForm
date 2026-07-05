import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { usePolicyQuery } from '@/lib/query/usePolicyQuery'
import { QUERY_POLICIES } from '@/lib/query/queryPolicy'
import { clearFlowFormQueryCache } from '@/lib/query/queryPersistence'
import type { components } from '@/api/generated/schema'

const meKeys = {
  profile: () => ['me', 'profile'] as const,
  verificationCheck: () => ['me', 'verification-check'] as const,
}

export function useMyProfile() {
  return usePolicyQuery({
    queryKey: meKeys.profile(),
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/account/profile')
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.profile,
  })
}

export function useUpdateProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: components['schemas']['UpdateProfileRequest']) => {
      const { data, error } = await apiClient.PATCH('/api/v1/account/profile', { body })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: meKeys.profile() })
    },
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST('/api/v1/account/change-password')
      if (error) throw error
      return data
    },
  })
}

export function useResendVerification() {
  return useMutation({
    mutationFn: async () => {
      const { error } = await apiClient.POST('/api/v1/account/resend-verification')
      if (error) throw error
    },
  })
}

// Live re-check against Auth0, gated to run only while the profile shows
// unverified. usePolicyQuery's staleTime + cooldownMs (queryPolicy.ts)
// handle the once-a-minute, refetch-on-mount/focus cadence -- no manual
// timers or storage needed.
export function useCheckVerification(enabled: boolean) {
  const queryClient = useQueryClient()
  return usePolicyQuery({
    queryKey: meKeys.verificationCheck(),
    enabled,
    queryFn: async () => {
      const { data, error } = await apiClient.POST('/api/v1/account/check-verification')
      if (error) throw error
      if (data.email_verified) {
        void queryClient.invalidateQueries({ queryKey: meKeys.profile() })
      }
      return data
    },
    policy: QUERY_POLICIES.verificationCheck,
  })
}

export function useDeleteAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { error } = await apiClient.DELETE('/api/v1/account')
      if (error) throw error
    },
    onSuccess: () => {
      void clearFlowFormQueryCache(queryClient)
    },
  })
}
