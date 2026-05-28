import type { ReactNode } from 'react'
import type { CurrentUserOut } from '@/api/generated/schema'
import { UserContext } from './userContextCore'
import type { UserContextValue } from './userContextCore'

export function UserProvider({
  user,
  avatarUrl,
  updateUser = () => {},
  children,
}: {
  user: CurrentUserOut
  avatarUrl: string | null
  updateUser?: (user: CurrentUserOut) => void
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
