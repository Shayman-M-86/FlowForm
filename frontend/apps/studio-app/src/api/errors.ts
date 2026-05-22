import type { ErrorResponse } from './generated/schema'

/**
 * Extract a display message from an openapi-fetch error.
 *
 * The backend's ErrorResponse shape is { code, message, details? }.
 * On 422 Pydantic failures, details.errors[] carries per-field messages.
 * Falls back to a generic string for anything unexpected.
 */
export function getErrorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (!error || typeof error !== 'object') return fallback

  const e = error as Partial<ErrorResponse> & { details?: { errors?: Array<{ message?: string; field?: string }> } }

  // 422 Pydantic field errors — surface the first field message
  const fieldErrors = e.details?.errors
  if (Array.isArray(fieldErrors) && fieldErrors.length > 0) {
    const first = fieldErrors[0]
    return first.field ? `${first.field}: ${first.message ?? 'invalid'}` : (first.message ?? fallback)
  }

  if (typeof e.message === 'string' && e.message) return e.message

  return fallback
}

/**
 * Map known backend error codes to user-friendly messages for a specific context.
 * Falls back to getErrorMessage for anything unrecognised.
 */
export function getInviteErrorMessage(error: unknown): string {
  const code = (error as Partial<ErrorResponse>)?.code

  switch (code) {
    case 'INVITATION_EXISTS':
      return 'A pending invitation already exists for this email address.'
    case 'ALREADY_A_MEMBER':
      return 'This person is already a member of the project.'
    case 'FORBIDDEN':
      return 'You do not have permission to invite members.'
    default:
      return getErrorMessage(error)
  }
}
