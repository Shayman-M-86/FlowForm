import { Card, CardStack } from '@flowform/ui'

export function ProjectsPage() {
  return (
    <main className="max-w-4xl mx-auto px-6 py-12">
      <h1>Projects</h1>
      <CardStack className="mt-8">
        <Card tone="muted">
          <p className="text-muted-foreground text-sm">No projects yet.</p>
        </Card>
      </CardStack>
    </main>
  )
}
