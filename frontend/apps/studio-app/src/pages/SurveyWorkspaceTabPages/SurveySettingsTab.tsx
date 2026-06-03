import { useState } from 'react'
import { useParams, useNavigate } from '@tanstack/react-router'
import { Card, Button, Input } from '@flowform/ui'
import { useHasProjectPermission } from '@/api/hooks/permissions'
import { useProject } from '@/api/hooks/projects'
import { useSurvey, useUpdateSurvey, useDeleteSurvey } from '@/api/hooks/surveys'
import { useRenderDebug } from '@/debug/useRenderDebug'

export function SurveySettingsTab() {
  useRenderDebug('SurveySettingsTab')
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/surveys/$surveySlug/settings' })
  const navigate = useNavigate()
  const { data: project } = useProject(slug)
  const { data: survey } = useSurvey(slug, surveySlug)
  const projectId = project?.id ?? null
  const canEdit   = useHasProjectPermission(projectId, 'survey:edit')
  const canDelete = useHasProjectPermission(projectId, 'survey:delete')

  const [title, setTitle] = useState<string | null>(null)
  const displayTitle = title ?? survey?.title ?? ''

  const updateSurvey = useUpdateSurvey(projectId, surveySlug)
  const deleteSurvey = useDeleteSurvey(projectId)

  function handleSave() {
    if (!survey) return
    updateSurvey.mutate({ title: displayTitle, visibility: null, public_slug: null })
  }

  function handleDelete() {
    if (!survey) return
    deleteSurvey.mutate(survey.id, {
      onSuccess: () => {
        void navigate({ to: '/projects/$slug', params: { slug } })
      },
    })
  }

  return (
    <section className="grid max-w-2xl gap-6 mx-auto">
      {canEdit && (
        <Card>
          <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">General</p>
          <div className="grid gap-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">Survey name</label>
              <Input
                value={displayTitle}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">Description</label>
              <Input placeholder="Optional internal description" />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">Internal notes</label>
              <Input placeholder="Notes visible only to project members" />
            </div>
          </div>
          <div className="mt-4">
            <Button
              variant="primary"
              size="sm"
              disabled={updateSurvey.isPending}
              onClick={handleSave}
            >
              {updateSurvey.isPending ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        </Card>
      )}

      {canDelete && (
        <Card>
          <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-destructive">Danger zone</p>
          <div className="grid gap-3">
            <div className="flex items-center justify-between gap-4 rounded-lg border border-destructive/30 p-3">
              <div>
                <p className="text-sm font-medium text-foreground">Delete survey</p>
                <p className="text-xs text-muted-foreground">Permanently delete this survey and all its versions.</p>
              </div>
              <Button
                variant="destructive"
                size="sm"
                disabled={deleteSurvey.isPending}
                onClick={handleDelete}
              >
                {deleteSurvey.isPending ? 'Deleting…' : 'Delete'}
              </Button>
            </div>
          </div>
        </Card>
      )}
    </section>
  )
}
