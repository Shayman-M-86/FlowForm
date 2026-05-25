import { useEffect, useMemo, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { Badge, Button, Card, Modal, Toast } from '@flowform/ui'
import { createMockSurvey, getMockSurveysForProject, type MockSurveySummary } from '@/api/mockData'
import { CreateSurveyForm, type CreateSurveyFields } from '@/components/CreateSurveyForm'
import { useRenderDebug } from '@/debug/useRenderDebug'

const PROJECT_CREATED_KEY = 'flowform:project-created'

interface SurveysTabProps {
  projectSlug: string
}

function surveyStatus(survey: MockSurveySummary): { label: string; variant: 'success' | 'muted' } {
  return survey.publishedVersionNumber !== null
    ? { label: 'Published', variant: 'success' }
    : { label: 'Draft', variant: 'muted' }
}

export function SurveysTab({ projectSlug }: SurveysTabProps) {
  useRenderDebug('SurveysTab', { projectSlug })
  const [refreshTick, setRefreshTick] = useState(0)
  const surveys = useMemo(
    () => getMockSurveysForProject(projectSlug),
    [projectSlug, refreshTick],
  )
  const [createdProjectName, setCreatedProjectName] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [createdSurveyTitle, setCreatedSurveyTitle] = useState<string | null>(null)

  useEffect(() => {
    const name = sessionStorage.getItem(PROJECT_CREATED_KEY)
    if (name) {
      sessionStorage.removeItem(PROJECT_CREATED_KEY)
      setCreatedProjectName(name)
    }
  }, [])

  const handleCreateSurvey = (data: CreateSurveyFields) => {
    const survey = createMockSurvey({
      projectSlug,
      title: data.title,
      slug: data.slug,
      description: data.description,
      initialStatus: 'draft',
    })
    setCreateOpen(false)
    setCreatedSurveyTitle(survey.title)
    setRefreshTick((tick) => tick + 1)
  }

  return (
    <section className="grid gap-4">
      {createdProjectName && (
        <Toast variant="success" onClose={() => setCreatedProjectName(null)}>
          Project &ldquo;{createdProjectName}&rdquo; created.
        </Toast>
      )}
      {createdSurveyTitle && (
        <Toast variant="success" onClose={() => setCreatedSurveyTitle(null)}>
          Survey &ldquo;{createdSurveyTitle}&rdquo; created.
        </Toast>
      )}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Surveys</h2>
          <p className="text-sm text-muted-foreground">{surveys.length} in this project</p>
        </div>
        <Button variant="primary" size="sm" icon="plus" onClick={() => setCreateOpen(true)}>
          New survey
        </Button>
      </div>
      <div className="grid gap-3 mx-auto w-3xl min-w-2">
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

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="New survey">
        <CreateSurveyForm onSubmit={handleCreateSurvey} />
      </Modal>
    </section>
  )
}
