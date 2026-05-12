import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/projects/$slug/$surveySlug/')({
  beforeLoad: ({ params }) => {
    throw redirect({
      to: '/projects/$slug/$surveySlug/overview',
      params,
    })
  },
})
