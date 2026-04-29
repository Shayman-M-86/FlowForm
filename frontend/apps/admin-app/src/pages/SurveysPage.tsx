import { Card, CardStack } from '@flowform/ui'

export function SurveysPage() {
  return (
    <main className="max-w-4xl mx-auto px-6 py-12">
      <h1>Surveys</h1>
      <CardStack className="mt-8">
        <Card tone="muted">
          <p className="text-muted-foreground text-sm">No surveys yet.</p>
        </Card>
      </CardStack>
    </main>
  )
}
