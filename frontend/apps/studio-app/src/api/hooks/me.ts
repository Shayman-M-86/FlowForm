import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { usePolicyQuery } from '@/lib/query/usePolicyQuery'
import { QUERY_POLICIES } from '@/lib/query/queryPolicy'
import { clearFlowFormQueryCache } from '@/lib/query/queryPersistence'
import type { components } from '@/api/generated/schema'

const meKeys = {
  profile: () => ['me', 'profile'] as const,
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
