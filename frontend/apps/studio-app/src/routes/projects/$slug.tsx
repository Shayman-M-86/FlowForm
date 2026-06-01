import { createFileRoute, Outlet, Link, useRouterState, useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'
import { setActiveProjectSlug } from '@/lib/storage/activeProject'
import { useProject } from '@/api/hooks/projects'
import { useHasProjectPermission } from '@/api/hooks/permissions'
import { Spinner, Card, TabSelector } from '@flowform/ui'
import { Breadcrumb } from '@/components/Breadcrumb'
import { useRenderDebug } from '@/debug/useRenderDebug'

function ProjectLayout() {
  useRenderDebug('ProjectLayout')
  const { slug } = Route.useParams()
  const { data: project, isPending, isError, error } = useProject(slug ?? null)
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const navigate = useNavigate()

  const projectId = project?.id ?? null
  const canViewSurveys = useHasProjectPermission(projectId, 'survey:view')
  const canManageMembers = useHasProjectPermission(projectId, 'project:manage_members')
  const canManageRoles = useHasProjectPermission(projectId, 'project:manage_roles')
  const canEditSettings = useHasProjectPermission(projectId, 'project:edit')
  const canDeleteProject = useHasProjectPermission(projectId, 'project:delete')

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

  const activeTab = ['surveys', 'members', 'roles', 'settings'].find((t) => pathname.includes(`/${t}`)) ?? 'surveys'

  const tabs = [
    { id: 'surveys',  label: 'Surveys',  disabled: !canViewSurveys,                      tooltip: 'You need survey:view permission to access surveys.' },
    { id: 'members',  label: 'Members',  disabled: !canManageMembers,                     tooltip: 'You need project:manage_members permission to manage members.' },
    { id: 'roles',    label: 'Roles',    disabled: !canManageRoles,                       tooltip: 'You need project:manage_roles permission to manage roles.' },
    { id: 'settings', label: 'Settings', disabled: !canEditSettings && !canDeleteProject, tooltip: 'You need project:edit or project:delete permission to access settings.' },
  ]

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
          items={tabs}
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
  useRenderDebug('ProjectNotFound')
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
