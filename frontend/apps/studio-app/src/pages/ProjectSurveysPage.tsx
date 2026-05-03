import { useParams } from '@tanstack/react-router'
import { Card, CardStack } from '@flowform/ui'

export function ProjectSurveysPage() {
  const { slug } = useParams({ from: '/projects/$slug/surveys' })

  return (
    <main className="max-w-4xl mx-auto px-6 py-12">
      <h1>Surveys</h1>
      <p className="text-muted-foreground mt-1 mb-8 text-sm">{slug}</p>
      <CardStack>
        <Card tone="muted">
          <p className="text-muted-foreground text-sm">No surveys yet.</p>
        </Card>
      </CardStack>
    </main>
  )
}
