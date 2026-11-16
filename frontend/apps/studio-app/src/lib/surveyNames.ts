export function toUrlSafeName(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

/** First of `base`, `base 1`, `base 2`, … that `isTaken` accepts. */
export function nextAvailableName(base: string, isTaken: (name: string) => boolean): string {
  for (let n = 0; ; n += 1) {
    const name = n === 0 ? base : `${base} ${n}`
    if (!isTaken(name)) return name
  }
}

/** Case-insensitive membership test over existing names. */
export function nameTakenIn(names: Iterable<string>): (name: string) => boolean {
  const taken = new Set([...names].map((name) => name.trim().toLowerCase()))
  return (name) => taken.has(name.toLowerCase())
}

/** Default new-survey name whose name and URL-safe name are both unused. */
export function nextDefaultSurveyName(existing: Array<{ title: string; public_slug?: string | null }>): string {
  const titleTaken = nameTakenIn(existing.map((survey) => survey.title))
  const takenSlugs = new Set(existing.flatMap((survey) => [toUrlSafeName(survey.title), survey.public_slug ?? '']))
  return nextAvailableName('My survey', (name) => titleTaken(name) || takenSlugs.has(toUrlSafeName(name)))
}

const DEFAULT_LINK_NAMES = {
  general_link: 'General Link',
  private_invite_link: 'Private Invite Link',
  authenticated_assigned_link: 'Authenticated Assigned Link',
} as const

export type DefaultNamedLinkType = keyof typeof DEFAULT_LINK_NAMES

/** Default name for a new access link, numbered past names the survey already uses. */
export function defaultLinkName(type: DefaultNamedLinkType, existingLinks: Array<{ name: string }>): string {
  return nextAvailableName(DEFAULT_LINK_NAMES[type], nameTakenIn(existingLinks.map((link) => link.name)))
}
