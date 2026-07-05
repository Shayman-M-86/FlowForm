// frontend/apps/studio-app/src/auth/UserContext.tsx
import { createContext, useContext, type ReactNode } from 'react'
import type { CurrentUserResponses } from '@/api/generated/schema'

export interface UserContextValue {
  user: CurrentUserResponses
  avatarUrl: string | null
  displayName: string
  updateUser: (user: CurrentUserResponses) => void
}

export const UserContext = createContext<UserContextValue | null>(null)

export function useCurrentUser(): UserContextValue | null {
  return useContext(UserContext)
}

export function UserProvider({
  user,
  avatarUrl,
  updateUser = () => {},
  children,
}: {
  user: CurrentUserResponses
  avatarUrl: string | null
  updateUser?: (user: CurrentUserResponses) => void
  children: ReactNode
}) {
  const value: UserContextValue = {
    user,
    avatarUrl,
    displayName: user.display_name ?? user.email,
    updateUser,
  }

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>
}
