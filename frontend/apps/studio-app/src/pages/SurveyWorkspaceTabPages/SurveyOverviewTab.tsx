import { Link, useParams } from '@tanstack/react-router'
import { Card, Badge, Button } from '@flowform/ui'
import { useProject } from '@/api/hooks/projects'
import { useSurvey } from '@/api/hooks/surveys'
import { useSurveyVersions } from '@/api/hooks/versions'
import { useRenderDebug } from '@/debug/useRenderDebug'

export function SurveyOverviewTab() {
  useRenderDebug('SurveyOverviewTab')
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/surveys/$surveySlug/overview' })

  const { data: project } = useProject(slug)
  const { data: survey } = useSurvey(slug, surveySlug)
  const { data: versions = [] } = useSurveyVersions(project?.id ?? 0, survey?.id ?? 0)

  const recentVersions = versions.slice(0, 3)
  const publishedVersion = versions.find((v) => v.status === 'published')
  const draftVersion = versions.find((v) => v.status === 'draft')
  const isPublished = publishedVersion != null
  const hasDraft = draftVersion != null

  return (
    <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
      {/* Left: status + quick actions */}
      <div className="grid gap-4">
        <Card>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Current status</p>
          <div className="grid gap-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">State</span>
              {isPublished ? (
                <Badge variant="success" size="xs">Published</Badge>
              ) : (
                <Badge variant="muted" size="xs">Draft</Badge>
              )}
            </div>
            {isPublished && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Published version</span>
                <span className="font-medium text-foreground">v{publishedVersion.version_number}</span>
              </div>
            )}
            {hasDraft && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Active draft</span>
                <span className="font-medium text-foreground">v{draftVersion.version_number}</span>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Public access</span>
              <span className="font-medium text-foreground">{isPublished ? 'Active' : 'None'}</span>
            </div>
          </div>
        </Card>

        <Card>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Quick actions</p>
          <div className="grid gap-2">
            {hasDraft && (
              <Link to="/projects/$slug/surveys/$surveySlug/builder" params={{ slug, surveySlug }}>
                <Button variant="secondary" size="sm" className="w-full justify-start">
                  Continue editing draft
                </Button>
              </Link>
            )}
            {isPublished && (
              <Button variant="secondary" size="sm" className="w-full justify-start">
                Preview live survey
              </Button>
            )}
            <Link to="/projects/$slug/surveys/$surveySlug/access" params={{ slug, surveySlug }}>
              <Button variant="secondary" size="sm" className="w-full justify-start">
                Manage public links
              </Button>
            </Link>
            <Link to="/projects/$slug/surveys/$surveySlug/responses" params={{ slug, surveySlug }}>
              <Button variant="secondary" size="sm" className="w-full justify-start">
                View responses
              </Button>
            </Link>
            {hasDraft && (
              <Button variant="primary" size="sm" className="w-full justify-start">
                Publish v{draftVersion.version_number}
              </Button>
            )}
          </div>
        </Card>
      </div>

      {/* Right: recent activity */}
      <div>
        <Card>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Recent activity</p>
          <div className="grid gap-3">
            {recentVersions.map((v) => (
              <div key={v.id} className="flex items-start gap-3">
                <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-muted-foreground">
                  {v.version_number}
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-foreground">
                    {v.status === 'draft' ? `v${v.version_number} draft edited` : `v${v.version_number} ${v.status}`}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(v.published_at ?? v.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </p>
                </div>
                <Badge
                  variant={v.status === 'published' ? 'success' : 'muted'}
                  size="xs"
                >
                  {v.status}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </section>
  )
}
