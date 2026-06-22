import { lazy, Suspense } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { Spinner } from '@flowform/ui'

const SurveyBuilderTab = lazy(() =>
  import('@/pages/SurveyWorkspaceTabPages/SurveyBuilderTab').then((m) => ({
    default: m.SurveyBuilderTab,
  }))
)

function SurveyBuilderTabRoute() {
  return (
    <Suspense fallback={<div className="flex justify-center py-16"><Spinner size={20} /></div>}>
      <SurveyBuilderTab />
    </Suspense>
  )
}

export const Route = createFileRoute('/_studio/projects/$slug/surveys/$surveySlug/builder')({
  component: SurveyBuilderTabRoute,
})
