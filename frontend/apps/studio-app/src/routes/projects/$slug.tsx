import { createFileRoute, Outlet } from '@tanstack/react-router'
import { useEffect } from 'react'
import { setActiveProjectSlug } from '@/lib/activeProject'

function ProjectLayout() {
  const { slug } = Route.useParams()

  useEffect(() => {
    setActiveProjectSlug(slug)
  }, [slug])

  return <Outlet />
}

export const Route = createFileRoute('/projects/$slug')({
  component: ProjectLayout,
})
