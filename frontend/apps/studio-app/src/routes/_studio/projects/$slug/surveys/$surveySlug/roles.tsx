import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/_studio/projects/$slug/surveys/$surveySlug/roles')({
  beforeLoad: ({ params }) => {
    throw redirect({
      to: '/projects/$slug/surveys/$surveySlug/access',
      params,
    })
  },
})
