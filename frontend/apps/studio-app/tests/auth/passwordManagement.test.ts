import { describe, expect, it } from 'vitest'

import { getPasswordManagement } from '@/auth/passwordManagement'

describe('getPasswordManagement', () => {
  it('recognizes an Auth0 database identity as locally password-managed', () => {
    expect(getPasswordManagement('auth0|user-123')).toEqual({
      managedExternally: false,
      providerName: null,
    })
  })

  it('labels Google identities explicitly', () => {
    expect(getPasswordManagement('google-oauth2|user-123')).toEqual({
      managedExternally: true,
      providerName: 'Google',
    })
  })

  it('keeps unknown external providers generic', () => {
    expect(getPasswordManagement('samlp|user-123')).toEqual({
      managedExternally: true,
      providerName: null,
    })
  })

  it('does not claim external management while the subject is unavailable', () => {
    expect(getPasswordManagement(undefined)).toEqual({
      managedExternally: false,
      providerName: null,
    })
  })
})
