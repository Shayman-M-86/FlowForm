import { useState } from 'react'
import { useParams } from '@tanstack/react-router'
import { Card, Button, Input, Toggle } from '@flowform/ui'
import { getMockSurvey } from '@/api/mockData'

export function SurveySettingsTab() {
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/$surveySlug/settings' })
  const [allowAnonymous, setAllowAnonymous] = useState(true)
  const [closeAfterDate, setCloseAfterDate] = useState(false)
  const survey = getMockSurvey(slug, surveySlug)
  const surveyTitle = survey?.title ?? surveySlug.replace(/-/g, ' ')

  return (
    <div className="grid max-w-2xl gap-6">
      {/* General */}
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

      {/* Behaviour */}
      <Card>
        <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Behaviour</p>
        <div className="grid gap-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-foreground">Allow anonymous responses</p>
              <p className="text-xs text-muted-foreground">Respondents do not need to be identified</p>
            </div>
            <Toggle checked={allowAnonymous} onChange={setAllowAnonymous} />
          </div>
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-foreground">Close after date</p>
              <p className="text-xs text-muted-foreground">Stop accepting responses after a specific date</p>
            </div>
            <Toggle checked={closeAfterDate} onChange={setCloseAfterDate} />
          </div>
        </div>
      </Card>

      {/* Danger zone */}
      <Card>
        <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-destructive">Danger zone</p>
        <div className="grid gap-3">
          <div className="flex items-center justify-between gap-4 rounded-lg border border-border p-3">
            <div>
              <p className="text-sm font-medium text-foreground">Archive survey</p>
              <p className="text-xs text-muted-foreground">Hide from the surveys list. Responses are preserved.</p>
            </div>
            <Button variant="secondary" size="sm">Archive</Button>
          </div>
          <div className="flex items-center justify-between gap-4 rounded-lg border border-destructive/30 p-3">
            <div>
              <p className="text-sm font-medium text-foreground">Delete survey</p>
              <p className="text-xs text-muted-foreground">Permanently delete this survey and all its versions.</p>
            </div>
            <Button variant="secondary" size="sm" className="border-destructive text-destructive hover:bg-destructive/10">
              Delete
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
