import { useParams } from '@tanstack/react-router'
import { Card } from '@flowform/ui'
import { getMockSurvey } from '@/api/mockData'

export function SurveyResponsesTab() {
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/$surveySlug/responses' })
  const survey = getMockSurvey(slug, surveySlug)
  const responseCount = survey?.responses ?? 0

  return (
    <div className="grid gap-6">
      <div>
        <h2 className="text-base font-semibold">Responses</h2>
        <p className="mt-0.5 text-sm text-muted-foreground">{responseCount} total submissions</p>
      </div>

      {responseCount === 0 ? (
        <Card tone="muted">
          <p className="text-sm text-muted-foreground">No responses yet.</p>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Total</p>
            <p className="text-3xl font-semibold text-foreground">{responseCount}</p>
          </Card>
          <Card>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Completed</p>
            <p className="text-3xl font-semibold text-foreground">{Math.round(responseCount * 0.9)}</p>
          </Card>
          <Card>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Partial</p>
            <p className="text-3xl font-semibold text-foreground">{Math.round(responseCount * 0.1)}</p>
          </Card>
        </div>
      )}

      <Card tone="muted">
        <p className="text-xs text-muted-foreground">
          Full response table and export will be available here. Responses are stored securely in a separate
          database and linked via a pseudonymous respondent ID.
        </p>
      </Card>
    </div>
  )
}
