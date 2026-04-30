import { Card, CardStack, Spinner, Badge } from '@flowform/ui'
import { useProjects } from '@/api/projects'

export function ProjectsPage() {
  const { data: projects, isPending, isError, error } = useProjects()

  return (
    <main className="max-w-4xl mx-auto px-6 py-12">
      <h1>Projects</h1>

      <CardStack className="mt-8">
        {isPending && (
          <div className="flex items-center gap-3 text-muted-foreground">
            <Spinner size={16} />
            <span className="text-sm">Loading projects…</span>
          </div>
        )}

        {isError && (
          <Card tone="muted">
            <p className="text-sm text-destructive">{error.message}</p>
          </Card>
        )}

        {projects?.length === 0 && (
          <Card tone="muted">
            <p className="text-muted-foreground text-sm">No projects yet.</p>
          </Card>
        )}

        {projects?.map((project) => (
          <Card key={project.id}>
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-semibold text-foreground">{project.name}</p>
                <p className="text-sm text-muted-foreground mt-0.5">{project.slug}</p>
              </div>
              <Badge variant="muted" size="xs">{project.id}</Badge>
            </div>
          </Card>
        ))}
      </CardStack>
    </main>
  )
}
