import type { ApiError } from './types'

export class ApiRequestError extends Error {
  public readonly status: number
  public readonly error: ApiError

  constructor(status: number, error: ApiError) {
    super(error.message)
    this.name = 'ApiRequestError'
    this.status = status
    this.error = error
  }

  get displayMessage(): string {
    if (this.error.errors && this.error.errors.length > 0) {
      return this.error.errors
        .map((e) => (e.field ? `${e.field}: ${e.message}` : e.message))
        .join('\n')
    }
    return this.error.message
  }
}
