// Re-exports for backwards compatibility with internal callers (mockData, client)
export type { CreateProjectRequest, ProjectOut } from './generated/schema'

// ── Errors ────────────────────────────────────────────────────────────────────

export interface ValidationErrorDetail {
  field: string
  message: string
  type: string
}

export interface ApiError {
  code: string
  message: string
  errors?: ValidationErrorDetail[]
  details?: Record<string, unknown>
}
