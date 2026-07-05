import { createFileRoute, redirect } from '@tanstack/react-router'
import { getActiveProjectSlug } from '@/lib/storage'

export const Route = createFileRoute('/_studio/')({
  beforeLoad: () => {
    const slug = getActiveProjectSlug()
    if (slug) {
      throw redirect({ to: '/projects/$slug', params: { slug } })
    }
    throw redirect({ to: '/projects' })
  },
})
