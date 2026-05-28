import { useContext } from 'react'
import { UserContext } from './userContextCore'
import type { UserContextValue } from './userContextCore'

export function useCurrentUser(): UserContextValue | null {
  return useContext(UserContext)
}
