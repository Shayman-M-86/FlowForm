const KEY = 'flowform.active_project'

export function getActiveProjectSlug(): string | null {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function setActiveProjectSlug(slug: string): void {
  try {
    localStorage.setItem(KEY, slug)
  } catch {
    // Active project memory is best-effort when localStorage is unavailable.
  }
}

export function clearActiveProjectSlug(): void {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // Active project memory is best-effort when localStorage is unavailable.
  }
}
