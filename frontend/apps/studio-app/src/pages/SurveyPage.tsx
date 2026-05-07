import { useParams } from '@tanstack/react-router'
import { Card, Button, Badge } from '@flowform/ui'
import { Breadcrumb } from '@/components/Breadcrumb'

export function SurveyPage() {
  const { slug, surveySlug } = useParams({ from: '/projects/$slug/$surveySlug' })

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <Breadcrumb segments={[
        { label: 'Projects', to: '/projects' },
        { label: slug, to: `/projects/${slug}` },
        { label: surveySlug, current: true },
      ]} />

      <div className="mt-3 flex items-center justify-between gap-4">
        <div>
          <h1 className="capitalize">{surveySlug.replace(/-/g, ' ')}</h1>
          <div className="mt-1"><Badge variant="muted" size="xs">Draft</Badge></div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm">Preview</Button>
          <Button variant="primary" size="sm">Publish</Button>
        </div>
      </div>

      <div className="mt-8 grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
        <Card>
          <p className="text-sm text-muted-foreground">Survey builder coming soon.</p>
        </Card>

        <div className="grid gap-4">
          <Card size="sm">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Responses</p>
            <p className="text-2xl font-semibold text-foreground">0</p>
          </Card>
          <Card size="sm">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Visibility</p>
            <p className="text-sm text-foreground">Private</p>
          </Card>
        </div>
      </div>
    </main>
  )
}
