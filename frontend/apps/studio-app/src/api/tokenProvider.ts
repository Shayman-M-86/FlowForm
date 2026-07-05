// frontend/apps/studio-app/src/api/tokenProvider.ts
let getAccessToken: (() => Promise<string>) | null = null

export function initApiAuth(getter: () => Promise<string>): void {
  getAccessToken = getter
}

export function getTokenGetter(): (() => Promise<string>) | null {
  return getAccessToken
}
