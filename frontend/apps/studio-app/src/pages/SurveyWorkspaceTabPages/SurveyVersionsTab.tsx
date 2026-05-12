import { useParams } from '@tanstack/react-router'
import { Badge, Button, Card } from '@flowform/ui'
import { getMockVersionsForSurvey, type MockVersion } from '@/api/mockData'

function versionBadge(status: MockVersion['status']) {
  if (status === 'published') return <Badge variant="success" size="xs">Published</Badge>
  if (status === 'draft') return <Badge variant="warning" size="xs">Draft</Badge>
  return <Badge variant="muted" size="xs">Archived</Badge>
}

function versionActions(v: MockVersion) {
  if (v.status === 'draft') {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" size="xs">Edit</Button>
        <Button variant="secondary" size="xs">Preview</Button>
        <Button variant="primary" size="xs">Publish</Button>
        <Button variant="secondary" size="xs">Delete</Button>
      </div>
    )
  }
  if (v.status === 'published') {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" size="xs">View live</Button>
        <Button variant="secondary" size="xs">Create draft copy</Button>
        <Button variant="secondary" size="xs">Archive</Button>
      </div>
    )
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button variant="secondary" size="xs">View</Button>
      <Button variant="secondary" size="xs">Restore as draft</Button>
    </div>
  )
}

export function SurveyVersionsTab() {
  const { surveySlug } = useParams({ from: '/projects/$slug/$surveySlug/versions' })
  const versions = getMockVersionsForSurvey(surveySlug)

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">Version history</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">{versions.length} versions</p>
        </div>
        <Button variant="primary" size="sm">New draft</Button>
      </div>

      <Card>
        <div className="divide-y divide-border">
          {/* Table header */}
          <div className="grid grid-cols-[80px_1fr_140px_140px_auto] gap-4 pb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <span>Version</span>
            <span>Status</span>
            <span>Created</span>
            <span>Published</span>
            <span>Actions</span>
          </div>

          {versions.map((v) => (
            <div
              key={v.id}
              className="grid grid-cols-[80px_1fr_140px_140px_auto] items-center gap-4 py-4"
            >
              <span className="text-sm font-semibold text-foreground">v{v.versionNumber}</span>
              <div className="flex items-center gap-2">
                {versionBadge(v.status)}
                <span className="text-xs text-muted-foreground">{v.questionCount} questions</span>
              </div>
              <span className="text-xs text-muted-foreground">
                {new Date(v.createdAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </span>
              <span className="text-xs text-muted-foreground">
                {v.publishedAt
                  ? new Date(v.publishedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                  : '—'}
              </span>
              {versionActions(v)}
            </div>
          ))}
        </div>
      </Card>

      <Card tone="muted">
        <p className="text-xs text-muted-foreground">
          Published versions are locked — they cannot be edited directly. To make changes, create a new draft,
          edit it, and publish. The previous published version will be archived automatically.
        </p>
      </Card>
    </div>
  )
}
