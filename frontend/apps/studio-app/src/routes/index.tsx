import { createFileRoute, redirect } from '@tanstack/react-router'
import { getActiveProjectSlug } from '@/lib/activeProject'

export const Route = createFileRoute('/')({
  beforeLoad: () => {
    const slug = getActiveProjectSlug()
    if (slug) {
      throw redirect({ to: '/projects/$slug', params: { slug } })
    }
    throw redirect({ to: '/projects' })
  },
})
