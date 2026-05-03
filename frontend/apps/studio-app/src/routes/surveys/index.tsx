import { createFileRoute } from '@tanstack/react-router'
import { SurveysPage } from '@/pages/SurveysPage'

export const Route = createFileRoute('/surveys/')({
  component: SurveysPage,
})
