import { createFileRoute, Outlet, Link } from '@tanstack/react-router'
import { useEffect } from 'react'
import { setActiveProjectSlug } from '@/lib/activeProject'

function ProjectLayout() {
  const { slug } = Route.useParams()

  useEffect(() => {
    setActiveProjectSlug(slug)
  }, [slug])

  return <Outlet />
}

function ProjectNotFound() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <p className="text-sm text-muted-foreground">Page not found.</p>
      <Link to="/projects" className="mt-3 block text-sm text-foreground underline">
        Back to projects
      </Link>
    </main>
  )
}

export const Route = createFileRoute('/projects/$slug')({
  component: ProjectLayout,
  notFoundComponent: ProjectNotFound,
})
