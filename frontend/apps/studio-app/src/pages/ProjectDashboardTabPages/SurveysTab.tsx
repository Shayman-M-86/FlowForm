import { useEffect, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { Badge, Button, Card, Modal, Spinner, Toast } from '@flowform/ui'
import { CreateSurveyForm, type CreateSurveyFields } from '@/components/CreateSurveyForm'
import { useRenderDebug } from '@/debug/useRenderDebug'
import { useProject } from '@/api/hooks/projects'
import { useCreateSurvey, useSurveys } from '@/api/hooks/surveys'
import type { SurveyOut } from '@/api/hooks/surveys'

const PROJECT_CREATED_KEY = 'flowform:project-created'

interface SurveysTabProps {
  projectSlug: string
}

function surveyStatus(survey: SurveyOut): { label: string; variant: 'success' | 'muted' } {
  return survey.published_version_id !== null
    ? { label: 'Published', variant: 'success' }
    : { label: 'Draft', variant: 'muted' }
}

export function SurveysTab({ projectSlug }: SurveysTabProps) {
  useRenderDebug('SurveysTab', { projectSlug })
  const [createdProjectName, setCreatedProjectName] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  const project = useProject(projectSlug)
  const projectId = project.data?.id ?? null
  const surveys = useSurveys(projectId ?? 0)
  const createSurvey = useCreateSurvey(projectId ?? 0)

  useEffect(() => {
    const name = sessionStorage.getItem(PROJECT_CREATED_KEY)
    if (name) {
      sessionStorage.removeItem(PROJECT_CREATED_KEY)
      setCreatedProjectName(name)
    }
  }, [])

  async function handleCreateSurvey(data: CreateSurveyFields) {
    if (projectId === null) return
    try {
      const survey = await createSurvey.mutateAsync({
        title: data.title,
        visibility: data.accessMode === 'public' ? 'public' : data.accessMode === 'link_only' ? 'link_only' : 'private',
        public_slug: data.accessMode === 'public' ? data.slug : null,
      })
      setCreateOpen(false)
      setToast(`Survey "${survey.title}" created.`)
    } catch {
      setToast('Failed to create survey. Please try again.')
    }
  }

  const surveyList = surveys.data ?? []

  return (
    <section className="grid gap-4">
      {createdProjectName && (
        <Toast variant="success" onClose={() => setCreatedProjectName(null)}>
          Project &ldquo;{createdProjectName}&rdquo; created.
        </Toast>
      )}
      {toast && (
        <Toast variant="success" onClose={() => setToast(null)}>
          {toast}
        </Toast>
      )}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Surveys</h2>
          <p className="text-sm text-muted-foreground">{surveyList.length} in this project</p>
        </div>
        <Button variant="primary" size="sm" icon="plus" onClick={() => setCreateOpen(true)}>
          New survey
        </Button>
      </div>

      {surveys.isLoading && (
        <div className="flex justify-center py-12">
          <Spinner size="md" />
        </div>
      )}

      {surveys.isError && (
        <p className="text-sm text-destructive">Failed to load surveys.</p>
      )}

      {!surveys.isLoading && !surveys.isError && (
        <div className="grid gap-3 mx-auto w-3xl min-w-2">
          {surveyList.map((survey) => {
            const status = surveyStatus(survey)
            return (
              <Link
                key={survey.id}
                to="/projects/$slug/surveys/$surveySlug/overview"
                params={{ slug: projectSlug, surveySlug: String(survey.id) }}
                className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-xl"
              >
                <Card interactive>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="truncate text-sm font-semibold text-foreground">{survey.title}</p>
                        <Badge variant={status.variant} size="xs">{status.label}</Badge>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Created {new Date(survey.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </p>
                    </div>
                  </div>
                </Card>
              </Link>
            )
          })}
          {surveyList.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-8">No surveys yet. Create your first one.</p>
          )}
        </div>
      )}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="New survey">
        <CreateSurveyForm onSubmit={(data) => void handleCreateSurvey(data)} />
      </Modal>
    </section>
  )
}
