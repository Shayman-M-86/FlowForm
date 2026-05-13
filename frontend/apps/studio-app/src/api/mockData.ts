import type { CreateProjectRequest, ProjectOut, SurveyOut, SurveyVersionOut, PublicLinkOut } from './types'

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

// ── Survey mock data ──────────────────────────────────────────────────────────

export interface MockSurveySummary {
  id: number
  slug: string
  title: string
  publishedVersionNumber: number | null
  draftVersionNumber: number | null
  responses: number
  updatedAt: string
  projectSlug: string
}

export const mockSurveys: MockSurveySummary[] = [
  {
    id: 1,
    slug: 'customer-onboarding-feedback',
    title: 'Customer onboarding feedback',
    publishedVersionNumber: 2,
    draftVersionNumber: 3,
    responses: 128,
    updatedAt: '2026-04-30T14:22:00Z',
    projectSlug: 'customer-research',
  },
  {
    id: 2,
    slug: 'product-discovery-intake',
    title: 'Product discovery intake',
    publishedVersionNumber: null,
    draftVersionNumber: 1,
    responses: 0,
    updatedAt: '2026-04-28T09:10:00Z',
    projectSlug: 'customer-research',
  },
  {
    id: 3,
    slug: 'quarterly-account-health-check',
    title: 'Quarterly account health check',
    publishedVersionNumber: 1,
    draftVersionNumber: null,
    responses: 54,
    updatedAt: '2026-04-25T11:45:00Z',
    projectSlug: 'customer-research',
  },
]

export function getMockSurvey(projectSlug: string, surveySlug: string): MockSurveySummary | undefined {
  return mockSurveys.find((s) => s.projectSlug === projectSlug && s.slug === surveySlug)
}

export function getMockSurveysForProject(projectSlug: string): MockSurveySummary[] {
  return mockSurveys.filter((s) => s.projectSlug === projectSlug)
}

// ── Version mock data ─────────────────────────────────────────────────────────

export interface MockVersion {
  id: number
  surveySlug: string
  versionNumber: number
  status: 'draft' | 'published' | 'archived'
  questionCount: number
  createdAt: string
  publishedAt: string | null
}

export const mockVersions: MockVersion[] = [
  {
    id: 13,
    surveySlug: 'customer-onboarding-feedback',
    versionNumber: 3,
    status: 'draft',
    questionCount: 12,
    createdAt: '2026-04-29T08:00:00Z',
    publishedAt: null,
  },
  {
    id: 12,
    surveySlug: 'customer-onboarding-feedback',
    versionNumber: 2,
    status: 'published',
    questionCount: 10,
    createdAt: '2026-04-10T10:00:00Z',
    publishedAt: '2026-04-11T09:30:00Z',
  },
  {
    id: 11,
    surveySlug: 'customer-onboarding-feedback',
    versionNumber: 1,
    status: 'archived',
    questionCount: 8,
    createdAt: '2026-03-28T12:00:00Z',
    publishedAt: '2026-03-29T11:00:00Z',
  },
  {
    id: 21,
    surveySlug: 'product-discovery-intake',
    versionNumber: 1,
    status: 'draft',
    questionCount: 5,
    createdAt: '2026-04-28T09:10:00Z',
    publishedAt: null,
  },
  {
    id: 31,
    surveySlug: 'quarterly-account-health-check',
    versionNumber: 1,
    status: 'published',
    questionCount: 7,
    createdAt: '2026-04-22T08:00:00Z',
    publishedAt: '2026-04-22T16:00:00Z',
  },
]

export function getMockVersionsForSurvey(surveySlug: string): MockVersion[] {
  return mockVersions.filter((v) => v.surveySlug === surveySlug)
}

// ── Public link mock data ─────────────────────────────────────────────────────

export interface MockPublicLink {
  id: number
  surveySlug: string
  tokenPrefix: string
  isActive: boolean
  assignedEmail: string | null
  expiresAt: string | null
  submissions: number
  createdAt: string
  url: string
}

export const mockPublicLinks: MockPublicLink[] = [
  {
    id: 1,
    surveySlug: 'customer-onboarding-feedback',
    tokenPrefix: 'abc12345',
    isActive: true,
    assignedEmail: null,
    expiresAt: null,
    submissions: 82,
    createdAt: '2026-04-11T09:30:00Z',
    url: 'https://flowform.app/s/abc12345',
  },
  {
    id: 2,
    surveySlug: 'customer-onboarding-feedback',
    tokenPrefix: 'def67890',
    isActive: false,
    assignedEmail: 'partner@acme.com',
    expiresAt: '2026-04-20T00:00:00Z',
    submissions: 46,
    createdAt: '2026-04-12T14:00:00Z',
    url: 'https://flowform.app/s/def67890',
  },
]

export function getMockPublicLinksForSurvey(surveySlug: string): MockPublicLink[] {
  return mockPublicLinks.filter((l) => l.surveySlug === surveySlug)
}

// ── Project member mock data ──────────────────────────────────────────────────

export interface MockProjectMember {
  id: number
  name: string
  email: string
  role: 'Owner' | 'Editor' | 'Viewer'
}

export const mockProjectMembers: MockProjectMember[] = [
  { id: 1, name: 'Testing User', email: 'testing@flowform.local', role: 'Owner' },
  { id: 2, name: 'Amelia Chen', email: 'amelia@example.com', role: 'Editor' },
  { id: 3, name: 'Marcus Lee', email: 'marcus@example.com', role: 'Editor' },
  { id: 4, name: 'Priya Shah', email: 'priya@example.com', role: 'Viewer' },
  { id: 5, name: 'Nora Evans', email: 'nora@example.com', role: 'Viewer' },
]

// ── Survey member mock data ───────────────────────────────────────────────────

export interface MockSurveyMember {
  id: number
  name: string
  email: string
  role: 'Manager' | 'Publisher' | 'Editor' | 'Viewer'
  inherited: boolean
}

export const mockSurveyMembers: MockSurveyMember[] = [
  { id: 1, name: 'Alex Chen', email: 'alex@example.com', role: 'Manager', inherited: true },
  { id: 2, name: 'Jamie Rivera', email: 'jamie@example.com', role: 'Publisher', inherited: false },
  { id: 3, name: 'Sam Park', email: 'sam@example.com', role: 'Editor', inherited: true },
  { id: 4, name: 'Taylor Obi', email: 'taylor@example.com', role: 'Viewer', inherited: false },
]
