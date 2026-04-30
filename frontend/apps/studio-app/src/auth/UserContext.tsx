import { createContext, useContext, type ReactNode } from 'react'
import type { CurrentUserOut } from '@/api/types'

interface UserContextValue {
  user: CurrentUserOut
  // Auth0 profile fields — available from the ID token
  avatarUrl: string | null
  displayName: string
}

const UserContext = createContext<UserContextValue | null>(null)

export function UserProvider({
  user,
  avatarUrl,
  children,
}: {
  user: CurrentUserOut
  avatarUrl: string | null
  children: ReactNode
}) {
  const value: UserContextValue = {
    user,
    avatarUrl,
    displayName: user.display_name ?? user.email,
  }

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>
}

export function useCurrentUser(): UserContextValue | null {
  return useContext(UserContext)
}
