import { useParams } from '@tanstack/react-router'
import { MemoryRouter } from 'react-router-dom'
import { NodePage } from '@flowform/builder'
import { Card, Button } from '@flowform/ui'
import { getMockSurvey, getMockVersionsForSurvey } from '@/api/mockData'
import { useRenderDebug } from '@/debug/useRenderDebug'

export function SurveyBuilderTab() {
  useRenderDebug('SurveyBuilderTab')
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/surveys/$surveySlug/builder' })
  const survey = getMockSurvey(slug, surveySlug)
  const versions = getMockVersionsForSurvey(surveySlug)
  const draftVersion = versions.find((v) => v.status === 'draft')

  if (!draftVersion) {
    return (
      <section className="grid gap-6">
        <Card tone="muted">
          <div className="flex flex-col items-start gap-3">
            <p className="text-sm text-muted-foreground">
              There is no draft version for this survey. Create a new draft to start editing.
            </p>
            {survey?.publishedVersionNumber != null && (
              <p className="text-xs text-muted-foreground">
                The published version (v{survey.publishedVersionNumber}) is locked and cannot be edited directly.
              </p>
            )}
            <Button variant="primary" size="sm">Create new draft</Button>
          </div>
        </Card>
      </section>
    )
  }

  return (
    <MemoryRouter initialEntries={['/node']}>
      <NodePage />
    </MemoryRouter>
  )
}
