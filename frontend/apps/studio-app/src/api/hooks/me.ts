import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { STALE } from '@/lib/query/queryClient'
import type { components } from '@/api/generated/schema'

const meKeys = {
  profile: () => ['me', 'profile'] as const,
}

export function useMyProfile() {
  return useQuery({
    queryKey: meKeys.profile(),
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/me/profile')
      if (error) throw error
      return data
    },
    staleTime: STALE.STATIC,
    meta: { persist: 'local' },
  })
}

export function useUpdateProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: components['schemas']['UpdateProfileRequest']) => {
      const { data, error } = await apiClient.PATCH('/api/v1/me/profile', { body })
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
      const { data, error } = await apiClient.POST('/api/v1/me/change-password')
      if (error) throw error
      return data
    },
  })
}

export function useResendVerification() {
  return useMutation({
    mutationFn: async () => {
      const { error } = await apiClient.POST('/api/v1/me/resend-verification')
      if (error) throw error
    },
  })
}

export function useDeleteAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { error } = await apiClient.DELETE('/api/v1/me')
      if (error) throw error
    },
    onSuccess: () => {
      queryClient.clear()
      window.localStorage.removeItem('flowform.query-cache')
    },
  })
}
