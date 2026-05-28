import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/projects/$slug/surveys/$surveySlug/')({
  beforeLoad: ({ params }) => {
    throw redirect({
      to: '/projects/$slug/surveys/$surveySlug/overview',
      params,
    })
  },
})
