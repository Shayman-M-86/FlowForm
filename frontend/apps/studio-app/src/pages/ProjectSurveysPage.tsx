import { useParams } from '@tanstack/react-router'
import { Card, CardStack } from '@flowform/ui'
import { Breadcrumb } from '@/components/Breadcrumb'
import { useProject } from '@/api/projects'

export function ProjectSurveysPage() {
  const { slug } = useParams({ from: '/projects/$slug' })
  const { data: project } = useProject(slug)
  const projectLabel = project?.name ?? slug

  return (
    <main className="max-w-4xl mx-auto px-6 py-12">
      <Breadcrumb segments={[
        { label: 'Projects', to: '/projects' },
        { label: projectLabel, to: `/projects/${slug}` },
        { label: 'Surveys', current: true },
      ]} />
      <h1 className="mt-3">Surveys</h1>
      <p className="text-muted-foreground mt-1 mb-8 text-sm">{slug}</p>
      <CardStack>
        <Card tone="muted">
          <p className="text-muted-foreground text-sm">No surveys yet.</p>
        </Card>
      </CardStack>
    </main>
  )
}
