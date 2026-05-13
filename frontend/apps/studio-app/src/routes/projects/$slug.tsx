import { createFileRoute, Outlet, Link, useRouterState, useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'
import { setActiveProjectSlug } from '@/lib/activeProject'
import { useProject } from '@/api/projects'
import { Spinner, Card, TabSelector } from '@flowform/ui'
import { Breadcrumb } from '@/components/Breadcrumb'

const TABS = [
  { id: 'surveys',  label: 'Surveys' },
  { id: 'members',  label: 'Members' },
  { id: 'roles',    label: 'Roles' },
  { id: 'settings', label: 'Settings' },
] as const

function ProjectLayout() {
  const { slug } = Route.useParams()
  const { data: project, isPending, isError, error } = useProject(slug ?? null)
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const navigate = useNavigate()

  useEffect(() => {
    setActiveProjectSlug(slug)
  }, [slug])

  // When inside a specific survey, the survey layout takes over — just pass through.
  const isInsideSurvey = /^\/projects\/[^/]+\/surveys\/[^/]+/.test(pathname)
  if (isInsideSurvey) return <Outlet />

  if (isPending) {
    return (
      <div className="flex min-h-[calc(100vh-56px)] items-center justify-center">
        <Spinner size={28} />
      </div>
    )
  }

  if (isError) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-12">
        <Card tone="muted">
          <p className="text-sm text-destructive">{error.message}</p>
        </Card>
      </main>
    )
  }

  const activeTab = TABS.find((t) => pathname.includes(`/${t.id}`))?.id ?? 'surveys'

  return (
    <main className="page-main">
      <Breadcrumb segments={[
        { label: 'Projects', to: '/projects' },
        { label: project.name, current: true },
      ]} />
      <div className="flex min-h-20 flex-col justify-between">
        <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h2 className="leading-tight">{project.name}</h2>
            <p className="mt-2 text-sm text-muted-foreground">{project.slug}</p>
          </div>
        </div>
        <TabSelector
          items={TABS.map((t) => ({ id: t.id, label: t.label }))}
          activeId={activeTab}
          onChange={(id) => navigate({ to: `/projects/${slug}/${id}` as any })}
        />
      </div>

      <div className="mt-6">
        <Outlet />
      </div>
    </main>
  )
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
