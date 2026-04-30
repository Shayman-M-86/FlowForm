import { useParams } from '@tanstack/react-router'
import { useProject } from '@/api/projects'
import { Spinner, Card } from '@flowform/ui'

export function ProjectDashboardPage() {
  const { slug } = useParams({ from: '/projects/$slug/' })
  const { data: project, isPending, isError, error } = useProject(slug)

  if (isPending) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-56px)]">
        <Spinner size={28} />
      </div>
    )
  }

  if (isError) {
    return (
      <main className="max-w-4xl mx-auto px-6 py-12">
        <Card tone="muted">
          <p className="text-sm text-destructive">{error.message}</p>
        </Card>
      </main>
    )
  }

  return (
    <main className="max-w-4xl mx-auto px-6 py-12">
      <h1>{project.name}</h1>
      <p className="text-muted-foreground mt-2 text-sm">{project.slug}</p>
    </main>
  )
}
