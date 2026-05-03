import type { CreateProjectRequest, ProjectOut } from './types'

export const mockProjects: ProjectOut[] = [
  {
    id: 101,
    name: 'Customer Research Portal',
    slug: 'customer-research',
    created_by_user_id: 0,
    created_at: '2026-04-18T10:00:00Z',
  },
  {
    id: 102,
    name: 'Employee Experience Program',
    slug: 'employee-experience',
    created_by_user_id: 0,
    created_at: '2026-04-20T09:30:00Z',
  },
  {
    id: 103,
    name: 'Partner Onboarding Feedback',
    slug: 'partner-onboarding-feedback',
    created_by_user_id: 0,
    created_at: '2026-04-22T08:45:00Z',
  },
]

export function getMockProject(ref: string | number): ProjectOut {
  const project = mockProjects.find((item) => item.id === Number(ref) || item.slug === String(ref))
  if (!project) throw new Error('Project not found')
  return project
}

export function createMockProject(body: CreateProjectRequest): ProjectOut {
  const name = body.name.trim()
  const slug = body.slug.trim()
  const timestamp = new Date().toISOString()

  return {
    id: Date.now(),
    name,
    slug,
    created_by_user_id: 0,
    created_at: timestamp,
  }
}
