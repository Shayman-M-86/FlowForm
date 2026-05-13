import { Link } from '@tanstack/react-router'
import { Badge, Button, Card } from '@flowform/ui'
import { getMockSurveysForProject, type MockSurveySummary } from '@/api/mockData'

interface SurveysTabProps {
  projectSlug: string
}

function surveyStatus(survey: MockSurveySummary): { label: string; variant: 'success' | 'muted' } {
  return survey.publishedVersionNumber !== null
    ? { label: 'Published', variant: 'success' }
    : { label: 'Draft', variant: 'muted' }
}

export function SurveysTab({ projectSlug }: SurveysTabProps) {
  const surveys = getMockSurveysForProject(projectSlug)

  return (
    <section className="grid max-w-6xl gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Surveys</h2>
          <p className="text-sm text-muted-foreground">{surveys.length} in this project</p>
        </div>
        <Button variant="primary" size="sm" icon="plus">New survey</Button>
      </div>
      <div className="grid gap-3">
        {surveys.map((survey) => {
          const status = surveyStatus(survey)
          const hasDraftChanges = survey.publishedVersionNumber !== null && survey.draftVersionNumber !== null
          return (
            <Link
              key={survey.id}
              to="/projects/$slug/surveys/$surveySlug/overview"
              params={{ slug: projectSlug, surveySlug: survey.slug }}
              className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-xl"
            >
              <Card interactive>
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-semibold text-foreground">{survey.title}</p>
                      <Badge variant={status.variant} size="xs">{status.label}</Badge>
                      {hasDraftChanges && <Badge variant="warning" size="xs">Draft changes</Badge>}
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Updated {new Date(survey.updatedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </p>
                  </div>
                  <div className="text-xs text-muted-foreground sm:text-right">
                    <p className="font-semibold text-foreground">{survey.responses}</p>
                    <p>Responses</p>
                  </div>
                </div>
              </Card>
            </Link>
          )
        })}
      </div>
    </section>
  )
}
