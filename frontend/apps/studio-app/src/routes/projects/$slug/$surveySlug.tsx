import { createFileRoute } from '@tanstack/react-router'
import { SurveyPage } from '@/pages/SurveyPage'

export const Route = createFileRoute('/projects/$slug/$surveySlug')({
  component: SurveyPage,
})
