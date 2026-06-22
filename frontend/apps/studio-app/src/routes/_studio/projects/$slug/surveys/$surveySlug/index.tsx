import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/_studio/projects/$slug/surveys/$surveySlug/')({
  beforeLoad: ({ params }) => {
    throw redirect({
      to: '/projects/$slug/surveys/$surveySlug/overview',
      params,
    })
  },
})
