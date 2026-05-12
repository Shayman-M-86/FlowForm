import { Link, useParams } from '@tanstack/react-router'
import { Badge, Button, Card, CardStack } from '@flowform/ui'
import { Breadcrumb } from '@/components/Breadcrumb'
import { useProject } from '@/api/projects'
import { getMockSurveysForProject, type MockSurveySummary } from '@/api/mockData'

function surveyStatus(survey: MockSurveySummary): { label: string; variant: 'success' | 'warning' | 'muted' } {
  if (survey.publishedVersionNumber !== null && survey.draftVersionNumber !== null) {
    return { label: 'Published', variant: 'success' }
  }
  if (survey.publishedVersionNumber !== null) {
    return { label: 'Published', variant: 'success' }
  }
  return { label: 'Draft', variant: 'muted' }
}

export function ProjectSurveysPage() {
  const { slug } = useParams({ from: '/projects/$slug' })
  const { data: project } = useProject(slug)
  const projectLabel = project?.name ?? slug
  const surveys = getMockSurveysForProject(slug)

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <Breadcrumb segments={[
        { label: 'Projects', to: '/projects' },
        { label: projectLabel, to: `/projects/${slug}` },
        { label: 'Surveys', current: true },
      ]} />

      <div className="mt-3 flex items-start justify-between gap-4">
        <div>
          <h1 className="mt-0">Surveys</h1>
          <p className="mt-1 text-sm text-muted-foreground">{projectLabel}</p>
        </div>
        <Button variant="primary" size="sm">New survey</Button>
      </div>

      <div className="mt-8">
        {surveys.length === 0 ? (
          <CardStack>
            <Card tone="muted">
              <p className="text-sm text-muted-foreground">No surveys yet. Create one to get started.</p>
            </Card>
          </CardStack>
        ) : (
          <div className="grid gap-3">
            {surveys.map((survey) => {
              const status = surveyStatus(survey)
              const hasDraftChanges = survey.publishedVersionNumber !== null && survey.draftVersionNumber !== null

              return (
                <Link
                  key={survey.id}
                  to="/projects/$slug/$surveySlug/overview"
                  params={{ slug, surveySlug: survey.slug }}
                  className="block rounded-xl border border-border bg-card p-4 text-left transition-colors hover:bg-(--bg-hover-highlight) focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-foreground">{survey.title}</p>
                        <Badge variant={status.variant} size="xs">{status.label}</Badge>
                        {hasDraftChanges && (
                          <Badge variant="warning" size="xs">Draft changes</Badge>
                        )}
                      </div>
                      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                        {survey.publishedVersionNumber !== null && (
                          <span>v{survey.publishedVersionNumber} live</span>
                        )}
                        {survey.draftVersionNumber !== null && (
                          <span>v{survey.draftVersionNumber} draft</span>
                        )}
                        <span>Updated {new Date(survey.updatedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                      </div>
                    </div>
                    <div className="shrink-0 text-right text-xs text-muted-foreground">
                      <p className="text-base font-semibold text-foreground">{survey.responses}</p>
                      <p>Responses</p>
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </main>
  )
}
