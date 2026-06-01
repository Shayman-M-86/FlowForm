import { useState } from 'react'
import { useParams } from '@tanstack/react-router'
import { Card, Button, Input, Toast, Toggle } from '@flowform/ui'
import { getMockPublicLinksForSurvey, getMockSurvey } from '@/api/mockData'
import { useHasProjectPermission } from '@/api/hooks/permissions'
import { useProject } from '@/api/hooks/projects'
import { useRenderDebug } from '@/debug/useRenderDebug'
import { SurveyAccessSettingsPanel } from '@/components/SurveyAccess'
import {
  SURVEY_ACCESS_CONCEPTS,
  SURVEY_ACCESS_ENTRIES,
  SURVEY_ACCESS_MODES,
  type SurveyAccessEntry,
  type SurveyAccessMode,
} from '@/lib/surveyAccessDesign'

function uniqueEntries(entries: SurveyAccessEntry[]): SurveyAccessEntry[] {
  return [...new Set(entries)]
}

export function SurveySettingsTab() {
  useRenderDebug('SurveySettingsTab')
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/surveys/$surveySlug/settings' })
  const { data: project } = useProject(slug)
  const projectId = project?.id ?? null
  const canEdit    = useHasProjectPermission(projectId, 'survey:edit')
  const canArchive = useHasProjectPermission(projectId, 'survey:archive')
  const canDelete  = useHasProjectPermission(projectId, 'survey:delete')
  const [savedAccessMode, setSavedAccessMode] = useState<SurveyAccessMode>('link_only')
  const [accessMode, setAccessMode] = useState<SurveyAccessMode>(savedAccessMode)
  const [allowAnonymous, setAllowAnonymous] = useState(true)
  const [closeAfterDate, setCloseAfterDate] = useState(false)
  const [accessWarning, setAccessWarning] = useState<string | null>(null)
  const survey = getMockSurvey(slug, surveySlug)
  const publicLinks = getMockPublicLinksForSurvey(surveySlug)
  const surveyTitle = survey?.title ?? surveySlug.replace(/-/g, ' ')
  const ResponseIdentityIcon = SURVEY_ACCESS_CONCEPTS.responseIdentity.icon
  const accessChanged = accessMode !== savedAccessMode

  function saveAccessChanges() {
    const currentEntries = new Set(SURVEY_ACCESS_MODES[savedAccessMode].allowedEntries)
    const nextEntries = new Set(SURVEY_ACCESS_MODES[accessMode].allowedEntries)
    const entriesInUse = uniqueEntries([
      ...publicLinks
        .filter((link) => link.isActive)
        .map((link) => (link.assignedEmail ? 'authenticated_assigned_link' : 'general_link') as SurveyAccessEntry),
      ...(savedAccessMode === 'public' ? ['public_slug' as SurveyAccessEntry] : []),
    ])
    const invalidatedEntries = entriesInUse.filter((entry) => currentEntries.has(entry) && !nextEntries.has(entry))

    setSavedAccessMode(accessMode)

    if (invalidatedEntries.length > 0) {
      const labels = invalidatedEntries.map((entry) => SURVEY_ACCESS_ENTRIES[entry].label).join(', ')
      setAccessWarning(`Access saved, but this change makes these existing access methods invalid: ${labels}.`)
      return
    }

    setAccessWarning(null)
  }

  return (
    <section className="grid max-w-2xl gap-6 mx-auto">
      {/* General */}
      {canEdit && (
        <Card>
          <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">General</p>
          <div className="grid gap-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-foreground">Survey name</label>
              <Input defaultValue={surveyTitle} />
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
            <Button variant="primary" size="sm">Save changes</Button>
          </div>
        </Card>
      )}

      {/* Danger zone */}
      {(canArchive || canDelete) && (
        <Card>
          <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-destructive">Danger zone</p>
          <div className="grid gap-3">
            {canArchive && (
              <div className="flex items-center justify-between gap-4 rounded-lg border border-border p-3">
                <div>
                  <p className="text-sm font-medium text-foreground">Archive survey</p>
                  <p className="text-xs text-muted-foreground">Hide from the surveys list. Responses are preserved.</p>
                </div>
                <Button variant="secondary" size="sm">Archive</Button>
              </div>
            )}
            {canDelete && (
              <div className="flex items-center justify-between gap-4 rounded-lg border border-destructive/30 p-3">
                <div>
                  <p className="text-sm font-medium text-foreground">Delete survey</p>
                  <p className="text-xs text-muted-foreground">Permanently delete this survey and all its versions.</p>
                </div>
                <Button variant="destructive" size="sm">Delete</Button>
              </div>
            )}
          </div>
        </Card>
      )}
    </section>
  )
}
