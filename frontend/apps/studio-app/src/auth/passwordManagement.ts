const PROVIDER_NAMES: Readonly<Record<string, string>> = {
  apple: 'Apple',
  facebook: 'Facebook',
  github: 'GitHub',
  'google-oauth2': 'Google',
  waad: 'Microsoft',
  windowslive: 'Microsoft',
}

export interface PasswordManagement {
  managedExternally: boolean
  providerName: string | null
}

export function getPasswordManagement(subject: string | undefined): PasswordManagement {
  const separatorIndex = subject?.indexOf('|') ?? -1
  if (!subject || separatorIndex <= 0) {
    return { managedExternally: false, providerName: null }
  }

  const provider = subject.slice(0, separatorIndex)
  if (provider === 'auth0') {
    return { managedExternally: false, providerName: null }
  }

  return {
    managedExternally: true,
    providerName: PROVIDER_NAMES[provider] ?? null,
  }
}
