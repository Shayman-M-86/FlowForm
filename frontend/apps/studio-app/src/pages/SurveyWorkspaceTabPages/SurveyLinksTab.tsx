import { useParams } from '@tanstack/react-router'
import { Badge, Button, Card } from '@flowform/ui'
import { getMockPublicLinksForSurvey, getMockSurvey } from '@/api/mockData'
import { useRenderDebug } from '@/debug/useRenderDebug'

export function SurveyLinksTab() {
  useRenderDebug('SurveyLinksTab')
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/surveys/$surveySlug/links' })
  const survey = getMockSurvey(slug, surveySlug)
  const links = getMockPublicLinksForSurvey(surveySlug)
  const isPublished = survey?.publishedVersionNumber != null

  return (
    <section className="grid gap-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Public links</h2>
          <p className="text-sm text-muted-foreground">Share this survey with respondents via public links.</p>
        </div>
        <Button variant="primary" size="sm" icon="plus" disabled={!isPublished}>
          Create link
        </Button>
      </div>

      {!isPublished && (
        <Card tone="muted">
          <p className="text-sm text-muted-foreground">
            Public links are only available for published surveys. Publish this survey first to create shareable links.
          </p>
        </Card>
      )}

      {isPublished && (
        <Card tone="muted">
          <p className="text-xs text-muted-foreground">
            Public links point to the currently published version (v{survey!.publishedVersionNumber}).
            Draft changes are not visible to respondents until published.
          </p>
        </Card>
      )}

      {links.length > 0 && (
        <div className="grid gap-4">
          {links.map((link, i) => (
            <Card key={link.id}>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {i === 0 && (
                      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Primary</span>
                    )}
                    <code className="rounded bg-muted px-1.5 py-0.5 text-xs text-foreground">{link.tokenPrefix}</code>
                    <Badge variant={link.isActive ? 'success' : 'muted'} size="xs">
                      {link.isActive ? 'Active' : 'Disabled'}
                    </Badge>
                    {link.assignedEmail && (
                      <span className="text-xs text-muted-foreground">{link.assignedEmail}</span>
                    )}
                  </div>
                  <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                    <span>Created {new Date(link.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                    <span>Expires {link.expiresAt ? new Date(link.expiresAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Never'}</span>
                    <span>{link.submissions} submissions</span>
                  </div>
                  <p className="mt-2 truncate font-mono text-xs text-muted-foreground">{link.url}</p>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <Button variant="secondary" size="xs">Copy link</Button>
                  <Button variant="secondary" size="xs">{link.isActive ? 'Disable' : 'Enable'}</Button>
                  <Button variant="secondary" size="xs">Regenerate</Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {isPublished && links.length === 0 && (
        <Card tone="muted">
          <p className="text-sm text-muted-foreground">No public links yet. Create one to start sharing this survey.</p>
        </Card>
      )}
    </section>
  )
}
