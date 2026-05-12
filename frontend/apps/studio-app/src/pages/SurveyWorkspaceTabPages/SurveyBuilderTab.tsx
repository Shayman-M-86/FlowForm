import { useParams } from '@tanstack/react-router'
import { Card, Badge, Button } from '@flowform/ui'
import { getMockSurvey, getMockVersionsForSurvey } from '@/api/mockData'

export function SurveyBuilderTab() {
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/$surveySlug/builder' })
  const survey = getMockSurvey(slug, surveySlug)
  const versions = getMockVersionsForSurvey(surveySlug)
  const draftVersion = versions.find((v) => v.status === 'draft')

  if (!draftVersion) {
    return (
      <div className="grid gap-4">
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
      </div>
    )
  }

  return (
    <div className="grid gap-4">
      {/* Builder header bar */}
      <div className="flex items-center justify-between rounded-xl border border-border bg-card px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-foreground">v{draftVersion.versionNumber} draft</span>
          <Badge variant="muted" size="xs">Draft</Badge>
          <span className="text-xs text-muted-foreground">Autosaved</span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm">Preview</Button>
          <Button variant="primary" size="sm">Publish</Button>
        </div>
      </div>

      {/* Builder workspace */}
      <div className="grid min-h-[560px] gap-4 lg:grid-cols-[220px_minmax(0,1fr)_260px]">
        {/* Left panel */}
        <Card>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Questions</p>
          <div className="grid gap-1">
            {Array.from({ length: draftVersion.questionCount }, (_, i) => (
              <button
                key={i}
                type="button"
                className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm text-muted-foreground transition-colors hover:bg-(--bg-hover-highlight) hover:text-foreground"
              >
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-muted text-xs font-medium">
                  {i + 1}
                </span>
                Question {i + 1}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="mt-3 flex w-full items-center gap-2 rounded-lg border border-dashed border-border px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:border-primary hover:text-primary"
          >
            + Add question
          </button>
        </Card>

        {/* Canvas */}
        <Card>
          <div className="flex h-full flex-col items-center justify-center gap-2 py-16">
            <p className="text-sm font-medium text-foreground">Survey builder</p>
            <p className="text-center text-xs text-muted-foreground">
              The full builder experience will be integrated from <code className="rounded bg-muted px-1 py-0.5">@flowform/builder</code> here.
            </p>
          </div>
        </Card>

        {/* Right panel */}
        <Card>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Question settings</p>
          <p className="text-xs text-muted-foreground">Select a question to edit its settings.</p>
        </Card>
      </div>
    </div>
  )
}
