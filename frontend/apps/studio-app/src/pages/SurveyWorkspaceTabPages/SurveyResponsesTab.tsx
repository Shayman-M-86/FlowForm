import { useParams } from '@tanstack/react-router'
import { Card } from '@flowform/ui'
import { useRenderDebug } from '@/debug/useRenderDebug'

// TODO: implement with real submissions API
// - fetch paginated submissions from GET /api/v1/projects/{project_id}/surveys/{survey_id}/submissions
// - derive total/completed/partial counts from response data
// - add response table with export

export function SurveyResponsesTab() {
  useRenderDebug('SurveyResponsesTab')
  useParams({ from: '/projects/$slug/surveys/$surveySlug/responses' })

  return (
    <section className="grid gap-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Responses</h2>
          <p className="text-sm text-muted-foreground">Not yet implemented</p>
        </div>
      </div>

      <Card tone="muted">
        <p className="text-sm font-medium text-muted-foreground">Coming soon</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Response counts, a full submission table, and export will appear here once the submissions
          API is wired up. Responses are stored securely in a separate database and linked via a
          pseudonymous respondent ID.
        </p>
      </Card>
    </section>
  )
}
