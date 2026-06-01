// frontend/apps/studio-app/src/auth/bootstrap/session.ts
import type { CurrentUserResponses } from '@/api/generated/schema'

const BOOTSTRAP_KEY = 'flowform.bootstrapped'
const USER_KEY = 'flowform.user'
const AVATAR_KEY = 'flowform.avatar'

export function getBootstrappedUserId(): string | null {
  try {
    return window.sessionStorage.getItem(BOOTSTRAP_KEY)
  } catch {
    return null
  }
}

export function markBootstrapped(userId: string): void {
  try {
    window.sessionStorage.setItem(BOOTSTRAP_KEY, userId)
  } catch {}
}

export function clearBootstrapped(): void {
  try {
    window.sessionStorage.removeItem(BOOTSTRAP_KEY)
    window.sessionStorage.removeItem(USER_KEY)
    window.sessionStorage.removeItem(AVATAR_KEY)
  } catch {}
}

export function saveUserToSession(user: CurrentUserResponses, avatarUrl: string | null): void {
  try {
    window.sessionStorage.setItem(USER_KEY, JSON.stringify(user))
    if (avatarUrl) {
      window.sessionStorage.setItem(AVATAR_KEY, avatarUrl)
    } else {
      window.sessionStorage.removeItem(AVATAR_KEY)
    }
  } catch {}
}

export function getUserFromSession(): CurrentUserResponses | null {
  try {
    const raw = window.sessionStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as CurrentUserResponses) : null
  } catch {
    return null
  }
}

export function getAvatarFromSession(): string | null {
  try {
    return window.sessionStorage.getItem(AVATAR_KEY)
  } catch {
    return null
  }
}
