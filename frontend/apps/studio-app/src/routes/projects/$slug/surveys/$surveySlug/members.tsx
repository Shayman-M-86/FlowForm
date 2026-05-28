import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/projects/$slug/surveys/$surveySlug/members')({
  beforeLoad: ({ params }) => {
    throw redirect({
      to: '/projects/$slug/surveys/$surveySlug/access',
      params,
    })
  },
})
