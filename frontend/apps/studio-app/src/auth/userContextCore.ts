import { createContext } from 'react'
import type { CurrentUserOut } from '@/api/generated/schema'

export interface UserContextValue {
  user: CurrentUserOut
  avatarUrl: string | null
  displayName: string
}

export const UserContext = createContext<UserContextValue | null>(null)
