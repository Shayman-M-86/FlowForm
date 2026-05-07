import { Link } from '@tanstack/react-router'
import { Badge } from '@flowform/ui'
import type { SurveySummary } from './types'

interface SurveysTabProps {
  projectSlug: string
}

const surveys: (SurveySummary & { slug: string })[] = [
  {
    id: 1,
    slug: 'customer-onboarding-feedback',
    name: 'Customer onboarding feedback',
    status: 'Published',
    visibility: 'Link only',
    responses: 128,
    updatedAt: 'Apr 30, 2026',
  },
  {
    id: 2,
    slug: 'product-discovery-intake',
    name: 'Product discovery intake',
    status: 'Draft',
    visibility: 'Private',
    responses: 0,
    updatedAt: 'Apr 28, 2026',
  },
  {
    id: 3,
    slug: 'quarterly-account-health-check',
    name: 'Quarterly account health check',
    status: 'Paused',
    visibility: 'Public',
    responses: 54,
    updatedAt: 'Apr 25, 2026',
  },
]

export function SurveysTab({ projectSlug }: SurveysTabProps) {
  return (
    <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
      <section className="grid gap-3">
        <div>
          <h2 className="text-base font-semibold">Surveys</h2>
          <p className="text-sm text-muted-foreground">{surveys.length} in this project</p>
        </div>
        <div className="grid gap-3 p-3">
          {surveys.map((survey) => (
            <Link
              key={survey.id}
              to="/projects/$slug/$surveySlug"
              params={{ slug: projectSlug, surveySlug: survey.slug }}
              className="block rounded-xl border border-border bg-card p-4 text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-semibold text-foreground">{survey.name}</p>
                    <Badge variant={survey.status === 'Published' ? 'success' : 'muted'} size="xs">
                      {survey.status}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {survey.visibility} · Updated {survey.updatedAt}
                  </p>
                </div>
                <div className="text-xs text-muted-foreground sm:text-right">
                  <p className="font-semibold text-foreground">{survey.responses}</p>
                  <p>Responses</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
